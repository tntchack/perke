Getting started
===============
If you are new to Perke, this is the place to begin. Currently, Perke
implements graph-based models. Let’s see a longer example to learn how
to use these models.

.. admonition:: Example

    .. code:: python

        from perke.unsupervised.graph_based import SingleRank

        # Define the set of valid part of speech tags to occur in the model.
        valid_pos_tags = {'N', 'Ne', 'AJ', 'AJe'}

        # 1. Create a SingleRank extractor.
        extractor = SingleRank(valid_pos_tags=valid_pos_tags)

        # 2. Load the text.
        extractor.load_text(input='text or path/to/input_file',
                            word_normalization_method=None)

        # 3. Select the longest sequences of nouns and adjectives as
        #    candidates.
        extractor.select_candidates()

        # 4. Weight the candidates using the sum of their words weights that
        #    are computed using random walk. In the graph, nodes are certain
        #    parts of speech (nouns and adjectives) that are connected if
        #    they co-occur in a window of 10 words.
        extractor.weight_candidates(window=10)

        # 5. Get the 10 highest weighted candidates as keyphrases
        keyphrases = extractor.get_n_best(n=10)

        for i, (weight, keyphrase) in enumerate(keyphrases):
            print(f'{i+1}.\t{keyphrase}, \t{weight}')

For other models, see the
`examples <https://github.com/alirezatheh/perke/tree/main/examples>`_
directory.
