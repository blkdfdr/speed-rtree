import os
import psutil
import osmium
import ctypes

# Osmium handler to extract roads with maxspeed
class SpeedHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.roads = []

    def way(self, w):
        if "highway" in w.tags:
            maxspeed = w.tags.get("maxspeed",None) or w.tags.get("zone:maxspeed", None)
            if maxspeed:
                coords = set()
                for n in w.nodes:
                    # use frozenlist for immutable coordinates in set
                    coords |= {(n.lon, n.lat)}
                self.roads.append({
                    "id": w.id,
                    "maxspeed": maxspeed,
                    "geometry": coords,
                    "name": w.tags.get("name","Unknown Road"),
                })

    # from https://github.com/osmcode/pyosmium/discussions/233#discussioncomment-11385914
    def apply_file_hardcore(self, filepath):
        def list_thread_ids():
            process = psutil.Process(os.getpid())
            threads = process.threads()
            return {thread.id for thread in threads}

        threads_before = list_thread_ids()

        self.apply_file(filepath, filters=[osmium.filter.EmptyTagFilter(), osmium.filter.EntityFilter(osmium.osm.WAY), osmium.filter.KeyFilter("highway")], locations=True)

        threads_after = list_thread_ids()
        new_threads = threads_after - threads_before

        def kill_thread(thread_id):
            # Access rights for terminating a thread
            THREAD_TERMINATE = 0x0001

            # Open the thread with terminate access
            handle = ctypes.windll.kernel32.OpenThread(THREAD_TERMINATE, False, thread_id)
            if not handle:
                print(f"Failed to open thread {thread_id}")
                return False

            # Terminate the thread
            result = ctypes.windll.kernel32.TerminateThread(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)

            if result == 0:
                print(f"Failed to terminate thread {thread_id}")
                return False

            return True

        # Terminate each new thread
        for thread_id in new_threads:
            kill_thread(thread_id)