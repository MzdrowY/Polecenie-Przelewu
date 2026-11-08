"""Syntetyczne dane do wizualnego sprawdzenia układu; NIE używać jako realnej wpłaty."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.pdfgen import generate_pdf
from app.models import Payment

def make_valid(prefix):
    bban = prefix.zfill(24)
    check = 98 - int(bban+'252100')%97
    return f'{check:02d}'+bban

if __name__=='__main__':
    dest=Path(__file__).resolve().parents[1]/"docs"/"PRZYKLAD_TESTOWY.pdf"
    demo=Payment(recipient="PRZYKLADOWY ODBIORCA",recipient_address="UL. TESTOWA 5, 00-001",
            recipient_account=make_valid("109000000000000000000001"),amount="125,50",
            currency="PLN",payer="PRZYKLADOWY WPLACAJACY",
            payer_address="UL. PROBNA 8, 00-002",payer_account="",title="PRZYKLADOWA WPLATA TESTOWA")
    generate_pdf(demo,dest)
    print(dest)
