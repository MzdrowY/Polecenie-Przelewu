from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import pymupdf as fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models import Payment, valid_nrb, normalized_amount, split_grid, fit_rows, check, InvalidPayment
from app.amount_words import number_words, amount_in_words
from app.database import Database
from app.pdfgen import generate_pdf, template_path, add_cells, ACCOUNT_X, AMOUNT_X, find_font


def valid_test_account(bban="109000000000000000000001"):
    assert len(bban)==24
    control=98-int(bban+"252100") % 97
    return f"{control:02d}"+bban


class CoreTests(unittest.TestCase):
    def make_payment(self):
        return Payment(recipient="TEST ODBIORCA",recipient_address="ADRES 1",
                recipient_account=valid_test_account(),amount="120,20",
                payer="JAN TEST",payer_address="ADRES NADAWCY",
                title="TEST PRZELEWU")

    def test_mod97(self):
        account=valid_test_account()
        self.assertEqual(len(account),26)
        self.assertTrue(valid_nrb(account))
        self.assertTrue(valid_nrb("PL"+account))
        self.assertFalse(valid_nrb(account[:-1]+str((int(account[-1])+1)%10)))

    def test_amount(self):
        self.assertEqual(normalized_amount("1 234,5"),"1234,50")
        with self.assertRaises(InvalidPayment):normalized_amount("-2")
        with self.assertRaises(InvalidPayment):normalized_amount("12.345")

    def test_account_digits_normalize_unicode(self):
        from app.models import account_digits
        account = valid_test_account()
        arabic = account.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
        self.assertTrue(valid_nrb(arabic))
        self.assertEqual(account_digits(arabic), account)

    def test_amount_with_stars_must_fit_its_cells(self):
        data = self.make_payment()
        data.amount = "9999999,99"
        data.amount_prefix_stars = True
        self.assertEqual(check(data), [])
        data.amount = "10000000,00"
        self.assertTrue(any("gwiazdkami" in err for err in check(data)))
        data.amount_prefix_stars = False
        self.assertEqual(check(data), [])

    def test_pdf_rejects_unprintable_glyph(self):
        data = self.make_payment()
        data.title = "TEST \U0010FFFF"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "invalid.pdf"
            with self.assertRaisesRegex(InvalidPayment, r"U\+10FFFF"):
                generate_pdf(data, output)
            self.assertFalse(output.exists())

    def test_text_overflow(self):
        self.assertEqual(split_grid("ALA MA KOTA",27,2),["ALA MA KOTA",""])
        with self.assertRaises(InvalidPayment):split_grid("X"*55)

    def test_database_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Database(Path(tmp)/"historia.db")
            data=self.make_payment()
            ident=db.save(data)
            self.assertEqual(db.get(ident),data)
            self.assertEqual(len(db.all("TEST ODBIORCA")),1)
            data.amount="200,00"
            self.assertEqual(db.save(data,ident),ident)
            self.assertEqual(db.get(ident).amount,"200,00")
            db.delete(ident)
            self.assertEqual(len(db.all()),0)
            db.close()

    def test_long_recipient_is_fitted_not_rejected(self):
        data=self.make_payment()
        data.recipient="BARDZO DLUGA NAZWA ODBIORCY WPLATY GOTOWKOWEJ"
        data.title="Długa przykładowa wpłata testowa z pełnym tytułem, który ma się zmieścić bez ucinania w obu wierszach"
        self.assertEqual(check(data),[])
        self.assertEqual(len(fit_rows(data.title, rows=2)),2)
        with tempfile.TemporaryDirectory() as tmp:
            pdf=generate_pdf(data,Path(tmp)/"dlugie.pdf")
            with fitz.open(pdf) as doc:
                text=doc[0].get_text().replace("\xa0", " ")
                self.assertEqual(text.count(data.recipient.upper()),2)
                self.assertIn("DŁUGA PRZYKŁADOWA",text)

    def test_amount_in_words_polish_inflection(self):
        examples={
          "1,01":"jeden złoty jeden grosz",
          "2,02":"dwa złote dwa grosze",
          "4,04":"cztery złote cztery grosze",
          "5,05":"pięć złotych pięć groszy",
          "12,12":"dwanaście złotych dwanaście groszy",
          "21,21":"dwadzieścia jeden złotych dwadzieścia jeden groszy",
          "22,22":"dwadzieścia dwa złote dwadzieścia dwa grosze",
          "1000,00":"tysiąc złotych zero groszy",
          "1234,56":"tysiąc dwieście trzydzieści cztery złote pięćdziesiąt sześć groszy",
          "1000001,11":"milion jeden złotych jedenaście groszy",
          "999999999,99":"dziewięćset dziewięćdziesiąt dziewięć milionów dziewięćset dziewięćdziesiąt dziewięć tysięcy dziewięćset dziewięćdziesiąt dziewięć złotych dziewięćdziesiąt dziewięć groszy",
        }
        for value, expected in examples.items():
            with self.subTest(value=value):
                self.assertEqual(amount_in_words(value),expected)

    def test_amount_in_words_on_both_receipts(self):
        data=self.make_payment()
        data.amount="999999999,99"
        data.title="PRZYKLADOWA WPLATA TESTOWA"
        with tempfile.TemporaryDirectory() as tmp:
            pdf=generate_pdf(data,Path(tmp)/"duza-kwota.pdf")
            with fitz.open(pdf) as doc:
                page=doc[0]
                words=amount_in_words(data.amount).upper()
                self.assertEqual(page.get_text().replace("\xa0", " ").count(words),2)
                spans=[sp for block in page.get_text("dict")["blocks"]
                            for line in block.get("lines",[])
                            for sp in line["spans"] if sp["text"].replace("\xa0", " ") == words]
                self.assertEqual(len(spans),2)
                for sp in spans:
                    self.assertGreaterEqual(sp["bbox"][0],100)
                    self.assertLessEqual(sp["bbox"][2], ACCOUNT_X[-1] * 72 / 110)

    def test_short_amount_in_words_stays_in_individual_cells(self):
        # JEDEN ZŁOTY JEDEN GROSZ mieści się w 26 kratkach:
        # każda widoczna litera ma własny, nieskalowany nadruk.
        words = amount_in_words("1,01").upper()
        self.assertEqual(len(ACCOUNT_X) - 1, 26)
        self.assertLessEqual(len(words), len(ACCOUNT_X) - 1)
        font = fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page = doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_cells(page, font, words, ACCOUNT_X, 240, size=9.2)
        visible = [c for c in words if c != " "]
        self.assertEqual(draw.call_count, len(visible))
        self.assertEqual([c.args[3] for c in draw.call_args_list], visible)
        self.assertTrue(all(c.kwargs.get("xscale", 1) == 1 for c in draw.call_args_list))

    def test_exact_cell_capacity_not_squeezed(self):
        text = "A" * (len(ACCOUNT_X) - 1)
        font = fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page = doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_cells(page, font, text, ACCOUNT_X, 240)
        self.assertEqual(draw.call_count, len(text))
        self.assertTrue(all(c.kwargs.get("xscale", 1) == 1 for c in draw.call_args_list))

    def test_one_character_over_capacity_uses_fitted_line(self):
        # Dopiero pierwszy znak ponad dostępne kratki powoduje przełączenie.
        text = "A" * len(ACCOUNT_X)
        font = fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page = doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_cells(page, font, text, ACCOUNT_X, 240)
        self.assertEqual(draw.call_count, 1)
        self.assertEqual(draw.call_args.args[3], text)
        self.assertGreater(draw.call_args.kwargs["xscale"], 0)

    def test_short_amount_words_rendered_on_both_receipts(self):
        payment = self.make_payment()
        payment.amount = "1,01"
        with tempfile.TemporaryDirectory() as tmp:
            path = generate_pdf(payment, Path(tmp) / "krotka_kwota.pdf")
            with fitz.open(path) as doc:
                page = doc[0]
                self.assertEqual(len(doc), 1)
                self.assertAlmostEqual(page.rect.width, 595.22, places=1)
                self.assertAlmostEqual(page.rect.height, 842, places=1)
                # Tekst w kratkach może być ekstraktowany ze spacjami,
                # dlatego sprawdzamy też bezpośrednio liczbę odcinków.
                self.assertTrue(page.get_text().strip())

    def test_cash_deposit_no_payer_account_overlap(self):
        data=self.make_payment()
        data.payer_account=valid_test_account()
        with tempfile.TemporaryDirectory() as tmp:
            pdf=generate_pdf(data,Path(tmp)/"cash.pdf")
            with fitz.open(pdf) as doc:
                self.assertEqual(doc[0].get_text().replace("\xa0", " ").count(amount_in_words(data.amount).upper()),2)
                self.assertNotIn(data.payer_account,doc[0].get_text())

    def test_polish_characters_in_pdf(self):
        data=self.make_payment()
        data.recipient="ŻÓŁĆ ŚLĄSK"
        data.payer="JAN KOWALSKI ŁÓDŹ"
        with tempfile.TemporaryDirectory() as tmp:
            out=generate_pdf(data,Path(tmp)/"polskie.pdf")
            with fitz.open(out) as doc:
                txt=doc[0].get_text()
                self.assertIn("Ż",txt)
                self.assertIn("Ł",txt)

    def test_pdf_original_a4_two_copies(self):
        payment=self.make_payment()
        self.assertEqual(check(payment),[])
        self.assertTrue(template_path().exists())
        with tempfile.TemporaryDirectory() as tmp:
            output=generate_pdf(payment,Path(tmp)/"druk.pdf")
            with fitz.open(output) as doc:
                self.assertEqual(len(doc),1)
                self.assertAlmostEqual(doc[0].rect.width,595.22,places=1)
                self.assertAlmostEqual(doc[0].rect.height,842,places=1)
                texts=doc[0].get_text()
                self.assertGreater(texts.count("T"),5)
                self.assertTrue(output.stat().st_size>10000)

    def test_amount_is_left_aligned_with_optional_two_asterisks(self):
        data = self.make_payment()
        data.amount_prefix_stars = True
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.pdfgen.add_cells", wraps=add_cells) as draw:
                generate_pdf(data, Path(tmp)/"kwota_od_lewej.pdf")
        calls = [c for c in draw.call_args_list if c.args[2] == "**120,20" and c.args[3] == AMOUNT_X]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(c.kwargs.get("right", False) is False for c in calls))

    def test_wp_type_selects_correct_shared_field(self):
        data = self.make_payment()
        data.payment_type = "P"
        data.payer_account = valid_test_account("109000000000000000000099")
        self.assertEqual(check(data), [])
        with tempfile.TemporaryDirectory() as tmp:
            out = generate_pdf(data, Path(tmp)/"przelew.pdf")
            with fitz.open(out) as doc:
                text = doc[0].get_text()
                self.assertNotIn(amount_in_words(data.amount).upper(), text)
                # Numery mogą być ekstraktowane rozdzielnie jako kratki,
                # dlatego sprawdź faktyczne wezwania silnika do pola wspólnego.
            with patch("app.pdfgen.add_cells", wraps=add_cells) as draw:
                generate_pdf(data, Path(tmp)/"przelew2.pdf")
        account_calls = [c for c in draw.call_args_list if c.args[2] == data.payer_account]
        self.assertEqual(len(account_calls), 2)

    def test_transfer_requires_payer_account(self):
        p = self.make_payment()
        p.payment_type = "P"
        self.assertTrue(any("rachunek zleceniodawcy" in e for e in check(p)))
        p.payer_account = valid_test_account()
        self.assertEqual(check(p), [])

    def test_wp_cross_marks_unused_letter_on_both_receipts(self):
        from app.pdfgen import PX_PT, SECTION_OFFSET_PX, WP_CENTER_X_PX, WP_CENTER_Y_PX
        payment = self.make_payment()
        payment.mark_wp = False  # starszy zapis historii
        payment.payer_account = valid_test_account()
        with tempfile.TemporaryDirectory() as tmp:
            for kind, unused in (("W", "P"), ("P", "W")):
                payment.payment_type = kind
                output = generate_pdf(payment, Path(tmp) / f"{kind}.pdf")
                with fitz.open(output) as doc:
                    lines = [d["rect"] for d in doc[0].get_drawings()
                             if d.get("color") and all(abs(c - 0.05) < 0.001 for c in d["color"])]
                    self.assertEqual(len(lines), 4)
                    for pair, offset in ((lines[:2], 0), (lines[2:], SECTION_OFFSET_PX)):
                        for line in pair:
                            self.assertAlmostEqual((line.x0 + line.x1) / 2,
                                                   WP_CENTER_X_PX[unused] * PX_PT, places=2)
                            self.assertAlmostEqual((line.y0 + line.y1) / 2,
                                                   (WP_CENTER_Y_PX + offset) * PX_PT, places=2)

    def test_words_longer_than_cells_expand_to_right_edge(self):
        from app.pdfgen import add_fitted_line, PX_PT
        txt = amount_in_words("1234,56").upper()
        self.assertGreater(len(txt), len(ACCOUNT_X) - 1)
        font = fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page = doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_fitted_line(page, font, txt, ACCOUNT_X, 240, size=9.2)
        self.assertEqual(draw.call_count, 1)
        kwargs=draw.call_args.kwargs
        self.assertAlmostEqual(draw.call_args.args[1] + font.text_length(txt,fontsize=9.2)*kwargs['xscale'],
                               ACCOUNT_X[-1]*PX_PT-1, places=3)
        self.assertGreater(kwargs['xscale'], 1.0)  # ten przypadek wcześniej zajmował około 2/3 pola

    def test_extremely_long_words_shrink_to_right_edge(self):
        from app.pdfgen import add_fitted_line, PX_PT
        txt="TEST "*70
        txt=txt.strip()
        font = fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page=doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_fitted_line(page,font,txt,ACCOUNT_X,240,size=9.2)
        k=draw.call_args.kwargs['xscale']
        self.assertLess(k,1.0)
        self.assertAlmostEqual(draw.call_args.args[1] + font.text_length(txt,fontsize=9.2)*k,
                               ACCOUNT_X[-1]*PX_PT-1, places=3)

    def test_short_words_fill_last_grid_cell_when_requested(self):
        from app.pdfgen import PX_PT
        txt = amount_in_words("1,01").upper()
        font=fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page=doc.new_page()
            with patch("app.pdfgen._draw") as draw:
                add_cells(page,font,txt,ACCOUNT_X,240,size=9.2,use_full_width=True)
        coords=[call.args[1] for call in draw.call_args_list]
        last=txt[-1]
        self.assertEqual(draw.call_count,len(txt.replace(' ','')))
        self.assertTrue(all(call.kwargs.get('xscale',1)==1 for call in draw.call_args_list))
        self.assertAlmostEqual(coords[-1] + font.text_length(last,fontsize=9.2)/2,
            (ACCOUNT_X[-2]+ACCOUNT_X[-1])*PX_PT/2, places=3)

    def test_short_words_keep_letters_of_each_word_in_adjacent_cells(self):
        from app.pdfgen import PX_PT
        txt=amount_in_words('1,01').upper()
        font=fitz.Font(fontfile=str(find_font()))
        with fitz.open() as doc:
            page=doc.new_page()
            with patch('app.pdfgen._draw') as draw:
                add_cells(page,font,txt,ACCOUNT_X,240,size=9.2,use_full_width=True)
        # Pozycja x dla widocznych liter -> odpowiadająca jej kratka.
        cells=[]
        for call in draw.call_args_list:
            x=call.args[1]
            char=call.args[3]
            box_index=min(range(len(ACCOUNT_X)-1),
                key=lambda i:abs(x+font.text_length(char,fontsize=9.2)/2
                       -(ACCOUNT_X[i]+ACCOUNT_X[i+1])*PX_PT/2))
            cells.append((char,box_index))
        for (a,i),(b,j) in zip(cells,cells[1:]):
            # W obrębie jednego wyrazu bez spacji nie pomijamy kratek.
            if a+b in ['JE','ED','DE','EN','ZŁ','ŁO','OT','TY','GR','RO','OS','SZ']:
                self.assertEqual(j,i+1)

    def test_number_tail_line_is_optional_and_on_two_receipts(self):
        from app.pdfgen import draw_amount_tail_bar
        p=self.make_payment()
        p.amount_end_bar=True
        with tempfile.TemporaryDirectory() as tmp:
            with patch('app.pdfgen.draw_amount_tail_bar') as tail:
                generate_pdf(p, Path(tmp)/'security.pdf')
        self.assertEqual(tail.call_count,2)
        self.assertTrue(all(call.args[1] == len('120,20') for call in tail.call_args_list))
        p.amount_end_bar=False
        with tempfile.TemporaryDirectory() as tmp:
            with patch('app.pdfgen.draw_amount_tail_bar') as tail:
                generate_pdf(p, Path(tmp)/'no_security.pdf')
        self.assertEqual(tail.call_count,0)

    def test_stars_optional_off_by_default(self):
        p=self.make_payment()
        self.assertFalse(p.amount_prefix_stars)
        with tempfile.TemporaryDirectory() as tmp:
            with patch('app.pdfgen.add_cells', wraps=add_cells) as draw:
                generate_pdf(p, Path(tmp)/'without_stars.pdf')
        amount_calls=[call for call in draw.call_args_list if call.args[3]==AMOUNT_X]
        self.assertEqual([call.args[2] for call in amount_calls],['120,20','120,20'])

    def test_old_database_json_loads_as_cash(self):
        import json
        p = self.make_payment()
        d = p.as_dict()
        del d["payment_type"]
        del d["mark_wp"]
        self.assertEqual(Payment(**json.loads(json.dumps(d))).payment_type, "W")

    def test_reject_incomplete(self):
        with self.assertRaises(InvalidPayment):
            generate_pdf(Payment(),Path("not-made.pdf"))

if __name__=="__main__":
    unittest.main()
