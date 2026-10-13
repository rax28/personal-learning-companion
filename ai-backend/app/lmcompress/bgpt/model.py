from __future__ import annotations

import random

import torch
from transformers import GPT2Model, GPT2LMHeadModel, PreTrainedModel

from .config import PATCH_SAMPLING_BATCH_SIZE, PATCH_SIZE
from .samplings import top_k_sampling, top_p_sampling, temperature_sampling


class PatchLevelDecoder(PreTrainedModel):
    """Patch-level decoder recovered from the supplied Code Ocean source."""

    def __init__(self, config):
        super().__init__(config)
        self.patch_embedding = torch.nn.Linear(PATCH_SIZE * (256 + 1), config.n_embd)
        torch.nn.init.normal_(self.patch_embedding.weight, std=0.02)
        self.base = GPT2Model(config)

    def forward(self, patches: torch.Tensor, masks=None) -> torch.Tensor:
        patches = torch.nn.functional.one_hot(patches, num_classes=256 + 1).to(self.dtype)
        patches = patches.reshape(len(patches), -1, PATCH_SIZE * (256 + 1))
        patches = self.patch_embedding(patches.to(self.device))
        if masks is None:
            return self.base(inputs_embeds=patches)
        return self.base(inputs_embeds=patches, attention_mask=masks)


class ByteLevelDecoder(PreTrainedModel):
    """Byte-level decoder recovered from the supplied Code Ocean source."""

    def __init__(self, config):
        super().__init__(config)
        self.special_token_id = 256
        self.base = GPT2LMHeadModel(config)

    def forward(self, encoded_patches: torch.Tensor, target_patches: torch.Tensor):
        target_patches = torch.cat(
            (torch.ones_like(target_patches[:, 0:1]) * self.special_token_id, target_patches),
            dim=1,
        )

        if PATCH_SAMPLING_BATCH_SIZE != 0 and PATCH_SAMPLING_BATCH_SIZE < target_patches.shape[0]:
            indices = list(range(len(target_patches)))
            random.shuffle(indices)
            selected_indices = sorted(indices[:PATCH_SAMPLING_BATCH_SIZE])
            target_patches = target_patches[selected_indices, :]
            encoded_patches = encoded_patches[selected_indices, :]

        inputs_embeds = torch.nn.functional.embedding(
            target_patches, self.base.transformer.wte.weight
        )
        inputs_embeds = torch.cat((encoded_patches.unsqueeze(1), inputs_embeds[:, 1:, :]), dim=1)
        return self.base(inputs_embeds=inputs_embeds, labels=target_patches)

    def generate(self, encoded_patch: torch.Tensor, tokens: torch.Tensor):
        encoded_patch = encoded_patch.reshape(1, 1, -1)
        tokens = tokens.reshape(1, -1)
        tokens = torch.nn.functional.embedding(tokens, self.base.transformer.wte.weight)
        tokens = torch.cat((encoded_patch, tokens[:, 1:, :]), dim=1)
        outputs = self.base(inputs_embeds=tokens)
        return torch.nn.functional.softmax(outputs.logits.squeeze(0)[-1], dim=-1)


class bGPTLMHeadModel(PreTrainedModel):
    """Hierarchical byte-level language model recovered from Code Ocean."""

    def __init__(self, encoder_config, decoder_config):
        super().__init__(encoder_config)
        self.special_token_id = 256
        self.patch_level_decoder = PatchLevelDecoder(encoder_config)
        self.byte_level_decoder = ByteLevelDecoder(decoder_config)

    def forward(self, patches: torch.Tensor, masks: torch.Tensor):
        patches = patches.reshape(len(patches), -1, PATCH_SIZE)
        encoded_patches = self.patch_level_decoder(patches, masks)["last_hidden_state"]

        # Clone before the source's in-place mutation so a caller can safely
        # reuse its attention mask across forward passes.
        left_shift_masks = masks * (masks.flip(1).cumsum(1).flip(1) > 1)
        masks = masks.clone()
        masks[:, 0] = 0
        encoded_patches = encoded_patches[left_shift_masks == 1]
        patches = patches[masks == 1]
        return self.byte_level_decoder(encoded_patches, patches)

    @torch.no_grad()
    def generate(self, patches: torch.Tensor, top_k=0, top_p=1, temperature=1.0):
        if patches.shape[-1] % PATCH_SIZE != 0:
            remainder = patches.shape[-1] % PATCH_SIZE
            tokens = patches[:, :, -remainder:].squeeze(0).squeeze(0)
            tokens = torch.cat((torch.tensor([self.special_token_id], device=self.device), tokens), dim=-1)
            patches = patches[:, :, :-remainder]
        else:
            tokens = torch.tensor([self.special_token_id], device=self.device)

        patches = patches.reshape(len(patches), -1, PATCH_SIZE)
        encoded_patches = self.patch_level_decoder(patches)["last_hidden_state"]
        generated_patch = []
        while True:
            prob = self.byte_level_decoder.generate(encoded_patches[0][-1], tokens)
            prob = top_k_sampling(prob.detach().cpu().numpy(), top_k=top_k, return_probs=True)
            prob = top_p_sampling(prob, top_p=top_p, return_probs=True)
            token = temperature_sampling(prob, temperature=temperature)
            generated_patch.append(token)
            if token == self.special_token_id or len(tokens) >= PATCH_SIZE:
                break
            tokens = torch.cat((tokens, torch.tensor([token], device=self.device)), dim=0)
        return generated_patch


class bGPTForClassification(PreTrainedModel):
    """Classification head recovered from the supplied Code Ocean source."""

    def __init__(self, encoder_config, label_size):
        super().__init__(encoder_config)
        self.patch_level_decoder = PatchLevelDecoder(encoder_config)
        self.classifier = torch.nn.Linear(encoder_config.n_embd, label_size)
        torch.nn.init.normal_(self.classifier.weight, std=0.02)

    def forward(self, patches: torch.Tensor):
        patches = patches.reshape(len(patches), -1, PATCH_SIZE)
        encoded_patches = self.patch_level_decoder(patches)["last_hidden_state"]
        encoded_patches = torch.mean(encoded_patches, dim=1)
        return self.classifier(encoded_patches)
