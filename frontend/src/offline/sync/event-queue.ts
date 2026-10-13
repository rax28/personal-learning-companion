export type SyncEvent={id:string;sequence:number;type:string;payload:unknown;createdAt:string};
const KEY='plc.sync-events';
export function enqueue(event:SyncEvent){const q=JSON.parse(localStorage.getItem(KEY)||'[]');q.push(event);localStorage.setItem(KEY,JSON.stringify(q))}
export function drain():SyncEvent[]{const q=JSON.parse(localStorage.getItem(KEY)||'[]');localStorage.removeItem(KEY);return q}
