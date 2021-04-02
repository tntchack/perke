from itertools import combinations
from typing import (Optional,
                    Literal,
                    Set,
                    Tuple,
                    List)

import networkx as nx
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist

from perke.base.extractor import Extractor
from perke.base.types import (TopicHeuristic,
                              HierarchicalClusteringMetric,
                              HierarchicalClusteringLinkageMethod)


class TopicRank(Extractor):
    """
    TopicRank keyphrase extractor.

    This model relies on a topical representation of the text. Candidate
    keyphrases are clustered into topics and used as nodes in a complete
    graph. A graph-based ranking model is applied to assign a
    significance weight to each topic. Keyphrases are then generated by
    selecting a candidate from each of the top ranked topics.

    Implementation of the SingleRank model described in:

    | Adrien Bougouin, Florian Boudin and Béatrice Daille
    | `TopicRank: Graph-Based Topic Ranking for Keyphrase Extraction
      <http://aclweb.org/anthology/I13-1062.pdf>`_
    | In proceedings of IJCNLP, pages 543-551, 2013

    Examples
    --------
    .. code:: python

        from perke.unsupervised.graph_based import TopicRank
        from perke.base.types import (WordNormalizationMethod,
                                      HierarchicalClusteringMetric,
                                      HierarchicalClusteringLinkageMethod)

        # Define the set of valid part of speech tags to occur in the model.
        valid_pos_tags = {'N', 'Ne', 'AJ', 'AJe'}

        # 1. Create a TopicRank extractor.
        extractor = TopicRank(valid_pos_tags=valid_pos_tags)

        # 2. Load the text.
        extractor.load_text(
            input='text or path/to/input_file',
            word_normalization_method=WordNormalizationMethod.stemming)

        # 3. Select the longest sequences of nouns and adjectives, that do
        #    not contain punctuation marks or stopwords as candidates.
        extractor.select_candidates()

        # 4. Build topics by grouping candidates with HAC (average linkage,
        #    jaccard distance, threshold of 1/4 of shared normalized words).
        #    Weight the topics using random walk, and select the first
        #    occurring candidate from each topic.
        extractor.weight_candidates(
            threshold=0.74,
            metric=HierarchicalClusteringMetric.jaccard,
            linkage_method=HierarchicalClusteringLinkageMethod.average)

        # 5. Get the 10 highest weighted candidates as keyphrases
        keyphrases = extractor.get_n_best(n=10)

    Attributes
    ----------
    graph: `nx.Graph`
        The topic graph

    topics: `list[list[str]]`
        List of topics
    """

    def __init__(self, valid_pos_tags: Optional[Set[str]] = None) -> None:
        """
        Initializes TopicRank.

        Parameters
        ----------
        valid_pos_tags: `set[str]`, optional
            Set of valid part of speech tags, defaults to nouns and
            adjectives. I.e. `{'N', 'Ne', 'AJ', 'AJe'}`.
        """

        super().__init__(valid_pos_tags)
        self.graph = nx.Graph()
        self.topics = []

    def select_candidates(self) -> None:
        """
        Selects longest sequences of nouns and adjectives as keyphrase
        candidates.
        """

        # Select sequence of adjectives and nouns
        self.select_candidates_with_longest_pos_sequences(
            valid_pos_tags=self.valid_pos_tags)

        # Filter candidates containing stopwords or punctuation marks
        self.filter_candidates(stopwords=self.stopwords)

    def vectorize_candidates(self) -> Tuple[List[str], np.ndarray]:
        """
        Vectorize the keyphrase candidates.

        Returns
        -------
        candidates: `list[str]`
            The list of candidates (canonical forms).

        candidate_matrix: `np.ndarray`
            Vectorized representation of the candidates.
        """

        # Build the vocabulary, i.e. setting the vector dimensions
        vocabulary = set()
        for candidate in self.candidates.values():
            for word in candidate.normalized_words:
                vocabulary.add(word)
        vocabulary = list(vocabulary)

        # Vectorize the candidates and sort for random issues
        candidates = list(self.candidates)
        candidates.sort()

        candidate_matrix = np.zeros((len(candidates), len(vocabulary)))
        for i, c in enumerate(candidates):
            for word in self.candidates[c].normalized_words:
                candidate_matrix[i, vocabulary.index(word)] += 1

        return candidates, candidate_matrix

    def cluster_topics(
            self,
            threshold: float = 0.74,
            metric: Literal[HierarchicalClusteringMetric.enums]
            = HierarchicalClusteringMetric.jaccard,
            linkage_method: Literal[HierarchicalClusteringLinkageMethod.enums]
            = HierarchicalClusteringLinkageMethod.average
    ) -> None:
        """
        Clusters candidates into topics.

        Parameters
        ----------
        threshold: `float`
            The minimum similarity for clustering, defaults to `0.74`,
            i.e. more than 1/4 of normalized word overlap similarity.

        metric: `str`
            The hierarchical clustering metric, defaults to `'jaccard'`
            See `perke.base.types.HierarchicalClusteringMetric` for
            available methods.

        linkage_method: `str`
            The hierarchical clustering linkage method, defaults to
            `'average'`. See
            `perke.base.types.HierarchicalClusteringLinkageMethod` for
            available methods.
        """

        # Handle content with only one candidate
        if len(self.candidates) == 1:
            self.topics.append(list(self.candidates))
            return

        # Vectorize the candidates
        candidates, candidate_matrix = self.vectorize_candidates()

        # Compute the distance matrix
        distance_matrix = pdist(candidate_matrix, metric)
        distance_matrix = np.nan_to_num(distance_matrix)

        # Compute the clusters
        clusters = linkage(distance_matrix, method=linkage_method)

        # Form flat clusters
        flat_clusters = fcluster(clusters, t=threshold, criterion='distance')

        # For each topic identifier
        for cluster_id in range(1, max(flat_clusters) + 1):
            self.topics.append([candidates[j] for j in range(len(flat_clusters))
                                if flat_clusters[j] == cluster_id])

    def build_topic_graph(self) -> None:
        """
        Build topic graph.
        """

        # Adding the nodes to the graph
        self.graph.add_nodes_from(range(len(self.topics)))

        # Loop through the topics to connect the nodes
        for i, j in combinations(range(len(self.topics)), 2):
            self.graph.add_edge(i, j, weight=0.0)
            for c_i in self.topics[i]:
                candidate_i = self.candidates[c_i]
                for c_j in self.topics[j]:
                    candidate_j = self.candidates[c_j]
                    for p_i in candidate_i.offsets:
                        for p_j in candidate_j.offsets:
                            gap = abs(p_i - p_j)
                            if p_i < p_j:
                                gap -= len(candidate_i.normalized_words) - 1
                            elif p_j < p_i:
                                gap -= len(candidate_j.normalized_words) - 1

                            self.graph[i][j]['weight'] += 1.0 / gap

    def weight_candidates(
            self,
            threshold: float = 0.74,
            metric: Literal[HierarchicalClusteringMetric.enums]
            = HierarchicalClusteringMetric.jaccard,
            linkage_method: Literal[HierarchicalClusteringLinkageMethod.enums]
            = HierarchicalClusteringLinkageMethod.average,
            topic_heuristic: Literal[TopicHeuristic.enums]
            = TopicHeuristic.first_occurring
    ) -> None:
        """
        Candidate ranking using random walk.

        Parameters
        ----------
        threshold: `float`
            The minimum similarity for clustering, defaults to 0.74.

        metric: `str`
            The hierarchical clustering metric, defaults to `'jaccard'`
            See `perke.base.types.HierarchicalClusteringMetric` for
            available methods.

        linkage_method: `str`
            The hierarchical clustering linkage method, defaults to
            `'average'`. See
            `perke.base.types.HierarchicalClusteringLinkageMethod` for
            available methods.

        topic_heuristic: `str`
            The heuristic for selecting the best candidate for each
            topic, defaults to first occurring candidate. See
            `perke.base.types.TopicHeuristic` for available heuristics.
        """

        # Cluster the candidates
        self.cluster_topics(threshold, metric, linkage_method)

        # Build the topic graph
        self.build_topic_graph()

        # Compute the word weights using random walk
        weights = nx.pagerank_scipy(self.graph, alpha=0.85, weight='weight')

        # Loop through the topics
        for i, topic in enumerate(self.topics):

            # Get the offsets of the topic candidates
            offsets = [self.candidates[c].offsets[0] for c in topic]

            # Get first candidate from topic
            if topic_heuristic == TopicHeuristic.frequent:

                # Get frequencies for each candidate within the topic
                frequencies = [len(self.candidates[c].all_words)
                               for c in topic]

                # Get the indices of the most frequent candidates
                max_frequency = max(frequencies)
                indices = [j for j, f in enumerate(frequencies)
                           if f == max_frequency]

                # Offsets of the indexes
                indices_offsets = [offsets[j] for j in indices]
                most_frequent = indices_offsets.index(min(indices_offsets))
                self.candidates[topic[most_frequent]].weight = weights[i]

            else:
                first = offsets.index(min(offsets))
                self.candidates[topic[first]].weight = weights[i]
