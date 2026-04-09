import sqlite3

conn = sqlite3.connect('ferrofluids.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all classified documents with all 6 classification codes (3 from each AI)
rows = cursor.execute('''
    SELECT 
        c.serial_number, 
        c.status,
        gpt.primary_code AS gpt_p, 
        gpt.secondary_code AS gpt_s, 
        gpt.tertiary_code AS gpt_t,
        claude.primary_code AS claude_p, 
        claude.secondary_code AS claude_s, 
        claude.tertiary_code AS claude_t
    FROM classifications c
    LEFT JOIN ai_results gpt ON c.serial_number = gpt.serial_number AND gpt.model_name = 'gpt'
    LEFT JOIN ai_results claude ON c.serial_number = claude.serial_number AND claude.model_name = 'claude'
    WHERE c.status IN ('agreed', 'disagreed', 'human_reviewed')
''').fetchall()

total = len(rows)
print(f"Total classified documents: {total}")
print()

# Method 1: Current approach - Primary code only
agreed_primary = sum(1 for r in rows if r['gpt_p'] == r['claude_p'])
disagreed_primary = total - agreed_primary

print("=" * 60)
print("METHOD 1: PRIMARY CODE ONLY (Current Approach)")
print("=" * 60)
print(f"Agreement: {agreed_primary} documents ({agreed_primary/total*100:.1f}%)")
print(f"Disagreement: {disagreed_primary} documents ({disagreed_primary/total*100:.1f}%)")
print()

# Method 2: 3-code overlap - any match counts as agreement
agreed_3code = 0
for r in rows:
    gpt_codes = [r['gpt_p'], r['gpt_s'], r['gpt_t']]
    claude_codes = [r['claude_p'], r['claude_s'], r['claude_t']]
    
    # Check if any GPT code matches any Claude code
    has_overlap = any(
        gpt_code == claude_code 
        for gpt_code in gpt_codes 
        for claude_code in claude_codes 
        if gpt_code and claude_code
    )
    
    if has_overlap:
        agreed_3code += 1

disagreed_3code = total - agreed_3code

print("=" * 60)
print("METHOD 2: 3-CODE EQUAL WEIGHT (Any Overlap = Agreement)")
print("=" * 60)
print(f"Agreement: {agreed_3code} documents ({agreed_3code/total*100:.1f}%)")
print(f"Disagreement: {disagreed_3code} documents ({disagreed_3code/total*100:.1f}%)")
print()

# Calculate the change
reduction_in_disagreements = disagreed_primary - disagreed_3code
percentage_point_reduction = (agreed_3code - agreed_primary) / total * 100

print("=" * 60)
print("IMPACT OF 3-CODE EQUAL WEIGHT APPROACH")
print("=" * 60)
print(f"Disagreements reduced by: {reduction_in_disagreements} documents")
print(f"Agreement rate increased by: {percentage_point_reduction:.1f} percentage points")
print(f"Relative reduction in disagreements: {reduction_in_disagreements/disagreed_primary*100:.1f}%")
print()

conn.close()
