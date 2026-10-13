const KEY='plc.learner-state';
export function loadLocalState<T=unknown>():T|null{const raw=localStorage.getItem(KEY);return raw?JSON.parse(raw):null}
export function saveLocalState(state:unknown){localStorage.setItem(KEY,JSON.stringify(state))}
