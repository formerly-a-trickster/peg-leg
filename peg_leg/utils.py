from typing import List

from peg_leg.ast import Clause


class ClauseQueue:
    queue: List[Clause]

    def __init__(self, *clauses):
        self.queue = []
        for clause in clauses:
            self.schedule(clause)

    def __len__(self):
        return len(self.queue)

    def __bool__(self):
        return bool(self.queue)

    def schedule(self, clause):
        for i, item in enumerate(self.queue):
            if clause.priority > item.priority:
                continue
            elif clause.priority == item.priority:
                return
            else:
                self.queue.insert(i, clause)
                return
        self.queue.append(clause)

    def pop(self) -> Clause:
        return self.queue.pop(0)
