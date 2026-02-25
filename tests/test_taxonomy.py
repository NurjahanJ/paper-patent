from app.taxonomy import (
    VALID_CODES,
    get_class_description,
    get_major_category,
    format_taxonomy_for_prompt,
)


class TestTaxonomy:
    def test_all_codes_present(self):
        expected = {11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                    37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51}
        assert VALID_CODES == expected

    def test_get_class_description(self):
        assert "Material" in get_class_description(11)
        assert "Chemistry" in get_class_description(11)

    def test_get_class_description_unknown(self):
        assert "Unknown" in get_class_description(999)

    def test_get_major_category(self):
        assert get_major_category(11) == "Material"
        assert get_major_category(21) == "Computation"
        assert get_major_category(37) == "Experimentation"
        assert get_major_category(38) == "Application"
        assert get_major_category(50) == "Review / Book"

    def test_format_taxonomy_for_prompt(self):
        text = format_taxonomy_for_prompt()
        assert "FERROFLUID" in text
        assert "11:" in text
        assert "51:" in text
        assert "MATERIAL" in text
        assert "APPLICATION" in text
