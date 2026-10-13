import pg from 'pg';
const { Pool } = pg;
export const pool = new Pool({ connectionString: process.env.DATABASE_URL || 'postgresql://plc:plc@localhost:5432/plc' });
export async function q<T extends pg.QueryResultRow = any>(text:string, params:any[]=[]):Promise<pg.QueryResult<T>> { return pool.query<T>(text,params); }
export async function initDb(){
  await q(`CREATE TABLE IF NOT EXISTS _plc_boot(id int primary key default 1)`);
  // Apply the auth migration at startup as well as shipping the SQL migration file.
  await q(`ALTER TABLE users ALTER COLUMN google_sub DROP NOT NULL`);
  await q(`ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT`);
}
