# Test fixtures

These HTML fixtures emulate the shape of HCSO's public-records pages so the
parser tests can run offline. **Names in every fixture are placeholders**:
`DOE`, `ROE`, `VOE` (Last) combined with `JOHN`, `JANE`, `SAMUEL`, etc.

## Rules

1. **Never commit a real HCSO record.** Even though the underlying data is
   public under ORC 149.43, JCStream's no-archive policy promises records
   disappear from the site when HCSO drops them from its roster. Git
   history would pin a real fixture indefinitely, breaking that promise.
2. **Scrub before commit.** If you copy a page off the live site to
   reproduce a parser bug, rename Last/First to the placeholder pattern,
   keep the rest (charge labels, ORC codes, photo base64, HTML shape).
3. **Inmate numbers are placeholders too.** Use 7-8 digit values that don't
   match any real HCSO id. The model now enforces digits-only, so format
   stays realistic.

## Files

- `list_smith.html` - surname search result page with three valid rows and
  one orphan row that lacks a detail link (must be skipped by parser).
- `detail_inmate.html` - inmate detail page with all bio fields populated,
  two charges, and the 274px-style inline photo placeholder
  (`UExBQ0VIT0xERVI=` decodes to `PLACEHOLDER`, not a JPEG; used to
  exercise the data-URI extraction path).
- `detail_no_photo.html` - inmate detail page with no inline image, used to
  cover the photo-carry-forward path in sweep `_fetch_one`.
