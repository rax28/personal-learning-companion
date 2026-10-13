export function mergeState<T extends {version:number}>(local:T,remote:T):T{return local.version>=remote.version?local:remote}
