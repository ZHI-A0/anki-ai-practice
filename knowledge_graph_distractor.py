from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

class KnowledgeGraph:
    def __init__(self):
        # 存储单词节点及其邻居
        self.graph: Dict[str, Set[str]] = {}
        # 可以存储词性信息等
        self.pos_info: Dict[str, str] = {}

    def add_node(self, word: str, pos: str = None) -> None:
        word_lower = word.lower()
        if word_lower not in self.graph:
            self.graph[word_lower] = set()
        if pos:
            self.pos_info[word_lower] = pos

    def add_edge(self, word1: str, word2: str) -> None:
        w1 = word1.lower()
        w2 = word2.lower()
        if w1 not in self.graph:
            self.graph[w1] = set()
        if w2 not in self.graph:
            self.graph[w2] = set()
        self.graph[w1].add(w2)
        self.graph[w2].add(w1)

    def get_neighbors(self, word: str) -> List[str]:
        return list(self.graph.get(word.lower(), []))

    def select_distractors(self, target: str, num: int = 3) -> List[str]:
        target_lower = target.lower()
        neighbors = self.graph.get(target_lower, set())
        distractors: List[str] = []
        used: Set[str] = {target_lower}

        for neighbor in neighbors:
            # 避免同词根的动词/形容词形式，可以通过 pos_info 或简单规则过滤
            if neighbor in used:
                continue
            if self.pos_info.get(neighbor) and self.pos_info.get(neighbor) == self.pos_info.get(target_lower):
                # 同词性且为变形可排除，简单过滤
                continue
            distractors.append(neighbor)
            used.add(neighbor)
            if len(distractors) >= num:
                break

        # 补齐不足
        if len(distractors) < num:
            for word in self.graph.keys():
                if word not in used:
                    distractors.append(word)
                    used.add(word)
                if len(distractors) >= num:
                    break

        return distractors[:num]