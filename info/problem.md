# Problem

Patents and research papers contain valuable knowledge, but it is often difficult to systematically organize and compare them. When reviewing large numbers of patents and research abstracts, it becomes challenging to:
- Categorize them consistently
- Identify thematic patterns
- See relationships between research and patented innovations
- Detect possible gaps between academic research and applied technology

Manual categorization is time-consuming and may introduce inconsistencies. At the same time, fully automated classification may not always be reliable without human oversight.
We need a structured method that allows us to organize patents and research abstracts accurately while maintaining academic reliability.

# Proposed Solution
I propose to build an AI-assisted system that helps classify patents and research abstracts into technical categories and then visually represents their relationships.
The system will work in the following way:
- Dual AI Classification
 Each patent and research abstract will be analyzed independently by two different AI models.
- Agreement Check (Consensus Process)
If both models agree on the classification, the result will be accepted automatically.
If the models disagree, the item will be flagged for review.
- Human Review (Human-in-the-Loop)
 Any disagreements will be presented for final human decision. This ensures academic accuracy and transparency while still benefiting from AI efficiency.
- Knowledge Graph Creation
After classifications are finalized, the system will generate a visual knowledge graph.
 - Each patent and research paper will appear as a node.
 - Categories will connect related documents.
 - The visualization will help reveal clusters, overlaps, and potential gaps between research and patents.
