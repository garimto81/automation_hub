// Supabase DB 스키마 적용 스크립트
import pg from 'pg';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const connectionString = process.env.DATABASE_URL ||
  'postgresql://postgres.feqpwuretyyejwrzcpum:wlwlvmfhejrtus@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres';

async function applySchema() {
  const client = new pg.Client({ connectionString, ssl: { rejectUnauthorized: false } });

  try {
    console.log('Connecting to Supabase DB...');
    await client.connect();
    console.log('Connected successfully!');

    // SQL 파일 읽기
    const sqlPath = path.join(__dirname, 'init-db.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');

    console.log('Applying schema...');
    await client.query(sql);
    console.log('Schema applied successfully!');

    // 테이블 확인
    const result = await client.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `);

    console.log('\nCreated tables:');
    result.rows.forEach(row => console.log(`  - ${row.table_name}`));

  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

applySchema();
