export type EvidenceSignal='understands'|'partially_understands'|'does_not_understand'|'misconception'|'uncertainty'|'successful_application'|'repeated_error';
export interface Evidence{concept:string;signal:EvidenceSignal;strength:number;confidence:number;description:string;source:'conversation'|'practice'|'system'}
export interface LearnerState{version:number;knowledge:Record<string,{mastery:number;confidence:number;evidenceCount:number}>;gaps:unknown[];misconceptions:unknown[];evidence:Evidence[];progress:unknown[]}
