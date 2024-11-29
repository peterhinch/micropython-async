# broker.py A message broker for MicroPython

# Copyright (c) 2024 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Inspired by the following
# https://www.joeltok.com/posts/2021-03-building-an-event-bus-in-python/

import asyncio
from primitives import Queue, type_coro


class Agent:
    pass


class Broker(dict):
    def subscribe(self, topic, agent):
        if not self.get(topic, False):
            self[topic] = {agent}
        else:
            self[topic].add(agent)

    def unsubscribe(self, topic, agent):
        try:
            self[topic].remove(agent)
            if len(self[topic]) == 0:
                del self[topic]
        except KeyError:
            pass  # Topic already removed

    def publish(self, topic, message):
        agents = self.get(topic, [])
        result = True
        for agent in agents:
            if isinstance(agent, asyncio.Event):
                agent.set()
                continue
            if isinstance(agent, Agent):  # User class
                agent.put(topic, message)  # Must support .put
                continue
            if isinstance(agent, Queue):
                if agent.full():
                    result = False
                else:
                    agent.put_nowait((topic, message))
                continue
            # agent is function, method, coroutine or bound coroutine
            res = agent(topic, message)
            if isinstance(res, type_coro):
                asyncio.create_task(res)
        return result
