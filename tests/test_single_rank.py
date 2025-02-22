from perke.unsupervised.graph_based import SingleRank


def test_original_article_default(text: str) -> None:
    extractor = SingleRank()
    extractor.load_text(input=text)
    extractor.select_candidates()
    extractor.weight_candidates()
    keyphrases = [keyphrase for keyphrase, weight in
                  extractor.get_n_best(n=3)]
    assert keyphrases == ['کاربردهای پردازش زبان طبیعی',
                          'کاربردهای متنوع پردازش زبان‌های طبیعی',
                          'پردازش زبان طبیعی']
