"""One clock for transitions, playback scheduling, and periodic UI updates."""

import time
from functools import lru_cache


def ease_out_cubic(progress):
    progress = max(0.0, min(1.0, progress))
    return 1 - (1 - progress) ** 3


def ease_in_out_quad(progress):
    progress = max(0.0, min(1.0, progress))
    return 2 * progress * progress if progress < .5 else 1 - (-2 * progress + 2) ** 2 / 2


@lru_cache(maxsize=8192)
def lerp_color(start, end, progress):
    progress = max(0.0, min(1.0, progress))
    return "#{:02x}{:02x}{:02x}".format(*(
        round(int(start[i:i + 2], 16) * (1 - progress) + int(end[i:i + 2], 16) * progress)
        for i in (1, 3, 5)))


class AnimationManager:
    def __init__(self, root):
        self.root = root
        self.jobs = {}
        self._after_id = None
        self._serial = 0
        self._closed = False
        self._ticking = False
        self._last_animation = time.perf_counter()
        self._wake_at = None
        self.fps = 60.0
        self.frames = 0
        self.max_frame_ms = 0.0

    def tween(self, key, duration, update, complete=None, easing=ease_out_cubic, delay=0):
        self.cancel(key)
        start = time.perf_counter() + delay
        self.jobs[key] = ["tween", start, max(.001, duration), update, complete, easing]
        if delay == 0:
            update(0.0)
        self._arm()
        return key

    def call_later(self, milliseconds, callback, key=None):
        self._serial += 1
        key = key or f"timer:{self._serial}"
        self.jobs[key] = ["timer", time.perf_counter() + milliseconds / 1000, callback]
        self._arm()
        return key

    def loop(self, key, callback, interval=16):
        if key not in self.jobs:
            now = time.perf_counter()
            self.jobs[key] = ["loop", now, interval / 1000, callback, now]
            self._arm()
        return key

    def cancel(self, key):
        self.jobs.pop(key, None)

    def cancel_prefix(self, prefix):
        for key in tuple(self.jobs):
            if str(key).startswith(prefix):
                self.cancel(key)

    def finish_tweens(self):
        for key, job in tuple(self.jobs.items()):
            if job[0] == "tween" and self.jobs.get(key) is job:
                self.jobs.pop(key, None)
                job[3](1.0)
                if job[4] is not None:
                    job[4]()

    def _arm(self):
        if self._closed or self._ticking or not self.jobs:
            return
        now = time.perf_counter()
        active = any(job[0] == "tween" and job[1] <= now for job in self.jobs.values())
        deadlines = [job[1] for job in self.jobs.values() if job[0] != "tween" or job[1] > now]
        if active:
            deadlines.append(max(now + .001, self._last_animation + .016))
        wake = min(deadlines) if deadlines else now + .016
        delay = max(1, min(2000, round((wake - now) * 1000)))
        if self._after_id is not None:
            if self._wake_at <= now + delay / 1000 + .001:
                return
            self.root.after_cancel(self._after_id)
        self._wake_at = now + delay / 1000
        self._after_id = self.root.after(delay, self._tick)

    def _tick(self):
        self._after_id = None
        self._wake_at = None
        if self._closed:
            return
        self._ticking = True
        now = time.perf_counter()
        delta = now - self._last_animation
        animation_due = delta >= .014
        if 0 < delta < .12:
            if animation_due:
                self.fps = self.fps * .85 + .15 / delta
        if animation_due:
            self._last_animation = now
        self.frames += 1
        try:
            for key, job in tuple(self.jobs.items()):
                if self.jobs.get(key) is not job or now < job[1]:
                    continue
                try:
                    if job[0] == "timer":
                        self.jobs.pop(key, None)
                        job[2]()
                    elif job[0] == "loop":
                        job[1] = now + job[2]
                        dt, job[4] = min(.1, now - job[4]), now
                        job[3](now, dt)
                    else:
                        if not animation_due:
                            continue
                        progress = min(1.0, (now - job[1]) / job[2])
                        job[3](job[5](progress))
                        if progress >= 1 and self.jobs.get(key) is job:
                            self.jobs.pop(key, None)
                            if job[4] is not None:
                                job[4]()
                except Exception:
                    self.jobs.pop(key, None)
                    import sys
                    self.root.report_callback_exception(*sys.exc_info())
        finally:
            self.max_frame_ms = max(self.max_frame_ms, (time.perf_counter() - now) * 1000)
            self._ticking = False
            self._arm()

    def close(self):
        self._closed = True
        self.jobs.clear()
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
