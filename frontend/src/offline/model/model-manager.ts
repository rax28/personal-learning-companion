export type ModelMode='online'|'offline';
export function chooseModel(online:boolean):ModelMode{return online?'online':'offline'}
