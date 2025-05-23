class MessageQueue:
    def __init__(self):
        self.queue = []

    def enqueue(self, message):
        self.queue.append(message)

    def dequeue(self):
        if not self.is_empty():
            return self.queue.pop(0)
        return None

    def is_empty(self):
        return len(self.queue) == 0

    def size(self):
        return len(self.queue)

    def clear(self):
        self.queue.clear()