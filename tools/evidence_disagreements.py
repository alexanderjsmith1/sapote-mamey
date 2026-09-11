"""Run the local evidence review view using this extracted bundle's package."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mamey.evidence_disagreements import main
if __name__=='__main__':main()
