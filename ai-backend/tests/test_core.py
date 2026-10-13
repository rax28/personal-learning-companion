from app.learner.learner_model import LearnerModel
from app.learner.evidence_extractor import EvidenceExtractor
from app.root_gap.root_gap_detector import RootGapDetector

def test_misconception_becomes_first_class_state():
    m=LearnerModel();e=EvidenceExtractor().extract('recursive calls execute simultaneously',{});m.apply(e);assert m.misconceptions[0]['status']=='open'

def test_root_gap_uses_prerequisites():
    m=LearnerModel();e={'concept':'chain rule','signal':'uncertainty','strength':.8,'confidence':.9,'description':'x'};m.apply(e);assert RootGapDetector().find(m,{},e)=='derivative'
