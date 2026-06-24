"""Run: python -m unittest tests.test_matching -v"""
import unittest

from src.matching import (
    alternative_variant_matches,
    pack_sizes_match,
    product_matches,
    score_search_result,
)


class TestMatching(unittest.TestCase):
    def test_pack_in_url_slug(self):
        url = "https://www.fressnapf.de/p/royal-canin-instinctive-adult-in-sosse-12x85-g-1099135"
        self.assertTrue(pack_sizes_match("12x85g", url))

    def test_pack_in_title(self):
        self.assertTrue(pack_sizes_match("12x85g", "Royal Canin Instinctive in Soße 12 x 85 g"))

    def test_royal_canin_instinctive_sosse(self):
        title = "ROYAL CANIN Instinctive Adult in Soße 12x85 g"
        url = "https://www.fressnapf.de/p/royal-canin-instinctive-adult-in-sosse-12x85-g-1099135"
        q = "Royal Canin Instinctive in Soße"
        self.assertTrue(product_matches(q, "12x85g", title, url=url))

    def test_rejects_joint_care_dog_food(self):
        title = "ROYAL CANIN JOINT CARE MAXI Trockenfutter"
        url = "https://www.zooroyal.de/p/joint-care/"
        q = "Royal Canin Instinctive in Soße"
        self.assertFalse(product_matches(q, "12x85g", title, url=url))

    def test_rejects_gelee_when_query_wants_sosse(self):
        title = "Royal Canin Instinctive in Gelee 12 x 85 g"
        q = "Royal Canin Instinctive in Soße"
        self.assertFalse(product_matches(q, "12x85g", title, url="https://zooplus.de/shop/x"))

    def test_rejects_feringa_wintermenue(self):
        title = "Limited Edition: Feringa Classic Meat Wintermenü Wild & Gans"
        url = "https://www.zooplus.de/shop/katzen/feringa/saison_menu/1408319"
        q = "Feringa Classic Meat Menü"
        self.assertFalse(product_matches(q, "24x400g", title, url=url))

    def test_feringa_fleisch_synonym(self):
        title = "Feringa Classic Fleisch Menü 12 x 400 g"
        q = "Feringa Classic Meat Menü"
        self.assertTrue(product_matches(q, "12x400g", title, url="https://zooplus.de/shop/x"))

    def test_allows_sparpaket_when_pack_matches(self):
        title = "Sparpaket Feringa Classic Meat Menü 12 x 400 g Geflügel"
        q = "Feringa Classic Meat Menü"
        self.assertTrue(product_matches(q, "12x400g", title, url="https://zooplus.de/shop/x"))

    def test_sparpaket_scores_higher_than_plain(self):
        plain = "Feringa Classic Meat Menü 12 x 400 g Geflügel"
        spar = "Sparpaket Feringa Classic Meat Menü 12 x 400 g Geflügel"
        q = "Feringa Classic Meat Menü"
        pack = "12x400g"
        url = "https://zooplus.de/shop/x"
        self.assertGreater(
            score_search_result(q, pack, spar, url=url),
            score_search_result(q, pack, plain, url=url),
        )

    def test_rc7_without_sosse_in_short_title(self):
        title = "ROYAL CANIN Instinctive 7+ 12x85 g"
        url = "https://www.fressnapf.de/p/royal-canin-instinctive-7-12x85-g-1101464"
        q = "Royal Canin Instinctive 7+ in Soße"
        self.assertTrue(product_matches(q, "12x85g", title, url=url))

    def test_cosma_sparpaket(self):
        title = "Sparpaket Cosma Asia in Jelly 12 x 400 g Thunfisch & Brasse"
        q = "Cosma Asia in Jelly"
        self.assertTrue(product_matches(q, "12x400g", title, url="https://zooplus.de/shop/x"))

    def test_wintermenue_is_alternative_not_primary(self):
        title = "Limited Edition: Feringa Classic Meat Wintermenü Wild & Gans"
        url = "https://www.zooplus.de/shop/katzen/feringa/saison_menu/1408319"
        q = "Feringa Classic Meat Menü"
        self.assertFalse(product_matches(q, "24x400g", title, url=url))
        self.assertTrue(alternative_variant_matches(q, "24x400g", title, url=url))

    def test_zooroyal_royal_canin_instinctive_title(self):
        title = "ROYAL CANIN INSTINCTIVE Katzenfutter nass in Soße - 12x85g"
        url = "https://www.zooroyal.de/p/royal-canin-instinctive-katzenfutter-nass-in-sosse-12x85g/1000076857/"
        q = "Royal Canin Instinctive in Soße"
        self.assertTrue(product_matches(q, "12x85g", title, url=url))

    def test_zooroyal_royal_canin_instinctive_7_title(self):
        title = "ROYAL CANIN INSTINCTIVE 7 Nassfutter in Soße für ältere Katzen - 12x85g"
        url = "https://www.zooroyal.de/p/royal-canin-instinctive-7-nassfutter-in-sosse-fuer-aeltere-katzen-12x85g/1000076863/"
        q = "Royal Canin Instinctive 7+ in Soße"
        self.assertTrue(product_matches(q, "12x85g", title, url=url))


if __name__ == "__main__":
    unittest.main()
