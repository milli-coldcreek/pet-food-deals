import unittest

from src.scrapers.zooplus import ZooplusScraper


class ZooplusScraperPriceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = ZooplusScraper()

    def test_royal_canin_extra_rabatt_beats_list_and_einzel(self) -> None:
        article = {
            "minArticlePriceRaw": 1549,
            "discountedPriceRaw": 1239,
            "offerPriceRaw": 1394,
        }
        list_price = self.scraper._list_price_from_article(article)
        deals = self.scraper._one_time_deals_from_article(article, list_price)
        best = min(deals, key=lambda row: row[0])
        self.assertEqual(list_price, 15.49)
        self.assertEqual(best[0], 12.39)
        self.assertEqual(best[1], 15.49)

    def test_ignores_zooplus_abo_subscription_prices(self) -> None:
        article = {
            "minArticlePriceRaw": 1749,
            "subscriptionPriceRaw": 1574,
            "aboPriceRaw": 1574,
        }
        list_price = self.scraper._list_price_from_article(article)
        deals = self.scraper._one_time_deals_from_article(article, list_price)
        self.assertEqual(list_price, 17.49)
        self.assertEqual(deals, [])

    def test_cosma_uses_list_price_without_subscription(self) -> None:
        article = {
            "minArticlePriceRaw": 1749,
            "subscriptionPriceRaw": 1574,
            "offerPriceRaw": 1529,
        }
        list_price = self.scraper._list_price_from_article(article)
        deals = self.scraper._one_time_deals_from_article(article, list_price)
        prices = [list_price] + [price for price, _ in deals]
        self.assertEqual(min(prices), 15.29)
        self.assertNotIn(15.74, prices)

    def test_rejects_steep_wrong_variant_discount(self) -> None:
        article = {"minArticlePriceRaw": 4399, "discountedPriceRaw": 1358}
        list_price = self.scraper._list_price_from_article(article)
        deals = self.scraper._one_time_deals_from_article(article, list_price)
        self.assertEqual(list_price, 43.99)
        self.assertEqual(deals, [])

    def test_einzel_delivery_flexible_block(self) -> None:
        from bs4 import BeautifulSoup

        html = (
            "<div><span>Einzellieferung</span><span>15,49 €</span>"
            "<span>-10%</span><span>13,94 €</span></div>"
        )
        price, original = self.scraper._einzel_delivery_price(
            BeautifulSoup(html, "html.parser")
        )
        self.assertEqual(price, 13.94)
        self.assertEqual(original, 15.49)

    def test_extra_rabatt_from_page_text(self) -> None:
        from bs4 import BeautifulSoup

        html = (
            "<div><span>15,49 €</span><span>-20% Extra-Rabatt aktivieren</span>"
            "<span>Einzellieferung</span><span>15,49 €</span>"
            "<span>-10%</span><span>13,94 €</span></div>"
        )
        soup = BeautifulSoup(html, "html.parser")
        price, original = self.scraper._extra_rabatt_price(soup, 15.49)
        self.assertEqual(price, 12.39)
        self.assertEqual(original, 15.49)

    def test_extra_rabatt_pct_near_verfuegbar_label(self) -> None:
        text = "% Extra-Rabatt verfügbar -20% Extra-Rabatt aktivieren"
        self.assertEqual(self.scraper._extra_rabatt_pct(text), 20)

    def test_infer_list_price_from_einzel_when_json_missing_list(self) -> None:
        from bs4 import BeautifulSoup

        html = (
            "<div><span>-20% Extra-Rabatt aktivieren</span>"
            "<span>Einzellieferung</span><span>15,49 €</span>"
            "<span>-10%</span><span>13,94 €</span></div>"
        )
        soup = BeautifulSoup(html, "html.parser")
        article = {"offerPriceRaw": 1394}
        list_price = self.scraper._infer_list_price(
            article, soup=soup, data={}, variant_id="113463.15"
        )
        self.assertEqual(list_price, 15.49)

    def test_extra_rabatt_beats_einzel_in_resolve(self) -> None:
        from bs4 import BeautifulSoup

        html = (
            "<div><span>15,49 €</span><span>-20% Extra-Rabatt aktivieren</span>"
            "<span>Einzellieferung</span><span>15,49 €</span>"
            "<span>-10%</span><span>13,94 €</span></div>"
        )
        article = {"minArticlePriceRaw": 1549, "offerPriceRaw": 1394}
        soup = BeautifulSoup(html, "html.parser")
        list_price = self.scraper._list_price_from_article(article)
        candidates: list[tuple[float, float | None]] = [(list_price, None)]
        candidates.extend(
            self.scraper._one_time_deals_from_article(article, list_price)
        )
        extra_price, extra_regular = self.scraper._extra_rabatt_price(soup, list_price)
        if extra_price is not None:
            candidates.append((extra_price, extra_regular))
        delivery_price, delivery_regular = self.scraper._einzel_delivery_price(soup)
        if delivery_price is not None:
            candidates.append((delivery_price, delivery_regular or list_price))
        best_price, best_original = min(candidates, key=lambda row: row[0])
        self.assertEqual(best_price, 12.39)
        self.assertEqual(best_original, 15.49)

    def test_regex_near_variant_finds_discount_fields(self) -> None:
        data = {
            "x": {"articleId": "113463.15", "meta": 1},
            "y": {"discountedPriceRaw": 1239, "minArticlePriceRaw": 1549},
        }
        fields = self.scraper._regex_prices_near_variant(data, "113463.15")
        self.assertEqual(fields.get("discountedPriceRaw"), 1239)
        self.assertEqual(fields.get("minArticlePriceRaw"), 1549)

    def test_resolve_picks_best_one_time_price(self) -> None:
        from bs4 import BeautifulSoup

        article = {
            "minArticlePriceRaw": 1549,
            "discountedPriceRaw": 1239,
            "offerPriceRaw": 1394,
        }
        merged = article
        list_price = self.scraper._list_price_from_article(merged)
        candidates = [(list_price, None)]
        candidates.extend(self.scraper._one_time_deals_from_article(merged, list_price))
        best_price, best_original = min(candidates, key=lambda row: row[0])
        self.assertEqual(best_price, 12.39)
        self.assertEqual(best_original, 15.49)

    def test_parses_cent_prices(self) -> None:
        self.assertEqual(self.scraper._parse_price_value(1549), 15.49)
        self.assertEqual(self.scraper._parse_price_value(1239), 12.39)

    def test_plausibility_blocks_per_piece_misread(self) -> None:
        name = "Sparpaket Feringa Classic Meat Menü 24 x 400 g"
        self.assertFalse(self.scraper._price_plausible(13.58, name, ""))
        self.assertTrue(self.scraper._price_plausible(39.59, name, ""))


if __name__ == "__main__":
    unittest.main()
