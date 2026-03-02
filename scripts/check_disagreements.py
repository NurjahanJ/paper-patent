"""Quick check of disagreement patterns."""
from app import db
from app.db.connection import transaction
from app.taxonomy import get_class_description

db.init_db()

with transaction() as conn:
    # Top disagreement pairs via ai_results join
    rows = conn.execute("""
        SELECT g.primary_code as gpt_p, cl.primary_code as claude_p, COUNT(1) as cnt
        FROM classifications c
        JOIN ai_results g ON c.serial_number = g.serial_number AND g.model_name = 'gpt'
        JOIN ai_results cl ON c.serial_number = cl.serial_number AND cl.model_name = 'claude'
        WHERE c.status = 'disagreed'
        GROUP BY g.primary_code, cl.primary_code
        ORDER BY cnt DESC
        LIMIT 15
    """).fetchall()

    # Same major category (first digit matches)
    same_major = conn.execute("""
        SELECT COUNT(1)
        FROM classifications c
        JOIN ai_results g ON c.serial_number = g.serial_number AND g.model_name = 'gpt'
        JOIN ai_results cl ON c.serial_number = cl.serial_number AND cl.model_name = 'claude'
        WHERE c.status = 'disagreed'
        AND g.primary_code / 10 = cl.primary_code / 10
    """).fetchone()[0]

    total_disagreed = conn.execute(
        "SELECT COUNT(1) FROM classifications WHERE status = 'disagreed'"
    ).fetchone()[0]

print(f"Total disagreements: {total_disagreed}")
print(f"Same major category: {same_major} ({100*same_major/total_disagreed:.0f}%)")
print(f"Different major category: {total_disagreed - same_major} ({100*(total_disagreed-same_major)/total_disagreed:.0f}%)")
print()
print(f"{'GPT':>5}  {'Claude':>6}  {'Count':>5}  GPT says -> Claude says")
print("-" * 75)
for r in rows:
    gpt_desc = get_class_description(r["gpt_p"]).split(" > ")[1][:25]
    claude_desc = get_class_description(r["claude_p"]).split(" > ")[1][:25]
    print(f"{r['gpt_p']:>5}  {r['claude_p']:>6}  {r['cnt']:>5}  {gpt_desc} -> {claude_desc}")
