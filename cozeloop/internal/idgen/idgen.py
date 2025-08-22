# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import math
import random
import time
import threading

_once = threading.Lock()
_id_generator = None


class IDGenerator:
    def gen_id(self):
        raise NotImplementedError


class MultiDeltaIDGenerator(IDGenerator):
    def __init__(self, id_generators, num):
        self.id_generators = id_generators
        self.index = 0
        self.num = num
        self.lock = threading.Lock()

    def gen_id(self):
        index = self._get_index()
        return self.id_generators[index].gen_id()

    def _get_index(self):
        with self.lock:
            self.index = (self.index + 1) % self.num
            return self.index


class AccumulateIDGenerator:
    def __init__(self, reseed_threshold, delta):
        self.random_number = lambda: random.randint(0, int(min(2**63 - 1, reseed_threshold)))
        self.seed = self.random_number()
        self.max_id = reseed_threshold
        self.delta = delta
        self.lock = threading.Lock()

    def gen_id(self):
        with self.lock:
            temp_id = self._add_and_get()
            if temp_id >= self.max_id:
                self._reset_seed()
                return self.gen_id()
            return temp_id

    def _add_and_get(self):
        self.seed += self.delta
        return self.seed

    def _reset_seed(self):
        self.seed = self.random_number()


def get_multiple_delta_id_generator() -> IDGenerator:
    global _id_generator
    with _once:
        if _id_generator is None:
            _id_generator = new_multiple_delta_id_generator(2**63 - 1, 1, 10)
    return _id_generator


def new_multiple_delta_id_generator(reseed_threshold, delta, num) -> IDGenerator:
    id_generators = []
    for _ in range(int(num)):
        id_generators.append(AccumulateIDGenerator(reseed_threshold, delta))
    return MultiDeltaIDGenerator(id_generators, num)
