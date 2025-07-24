import sqlite3

import h3
import numpy as np
from haversine import *

roads_index = """CREATE VIRTUAL TABLE roads_index USING rtree(
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             minX, maxX, 
             minY, maxY,
             +road_id BIGINT,
             +startX REAL,
             +startY REAL,
             +endX REAL,
             +endY REAL,
           );"""

roads = """CREATE TABLE roads (
                id INTEGER PRIMARY KEY,
                maxspeed TEXT,
                name TEXT,
                h3 BIGINT
            );"""


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    start = np.array((y1,x1))
    end = np.array((y2,x2))
    p = np.array((py,px))

    part = end - start
    normed = part / np.linalg.norm(part)
    t = np.dot(p - start, normed)

    if t < 0:
        return haversine(p, start, Unit.METERS), (start, p)
    elif t > 1:
        return haversine(p, end, Unit.METERS), (end, p)
    projected = t * normed
    return haversine(projected + start, p, Unit.METERS), (projected+start, p)


class Schema:
    def __init__(self, db_path="roads.sqlite"):
        self.conn = sqlite3.connect(db_path)

    def setup_tables(self):
        self.conn.execute("DROP TABLE IF EXISTS roads_index")
        self.conn.execute("DROP TABLE IF EXISTS roads")
        self.conn.execute("DROP TABLE IF EXISTS roads_polys")
        self.conn.execute(roads)
        self.conn.execute(roads_index)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def insert_roads(self,road_dicts, schema=None):
        coord_id = 0
        cursor = self.conn.cursor()

        for road in road_dicts:
            road_id = road["id"]
            road_name = road["name"]
            road_coords = list(road["geometry"])
            road_maxspeed = road["maxspeed"]
            road_h3 = h3.latlng_to_cell(road_coords[0][1], road_coords[0][0], 5)
            cursor.execute("INSERT INTO roads VALUES (?, ?, ?, ?)", (road_id, road_maxspeed, road_name, road_h3))

            # create coord pairs to get the bboxes
            if len(road_coords)==1:
                return
            road_indices = []
            for i, coord in enumerate(road_coords[0:]):
                cur_rect = (coord, road_coords[i-1])
                coord_lon_min = min(cur_rect[0][0], cur_rect[1][0])
                coord_lat_min = min(cur_rect[0][1], cur_rect[1][1])
                coord_lon_max = max(cur_rect[0][0], cur_rect[1][0])
                coord_lat_max = max(cur_rect[0][1], cur_rect[1][1])

                road_indices += [(coord_id, coord_lon_min, coord_lon_max, coord_lat_min, coord_lat_max, road_id, cur_rect[0][0], cur_rect[0][1], cur_rect[1][0], cur_rect[1][1])]
                coord_id += 1
            cursor.executemany("INSERT INTO roads_index VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", road_indices)
        self.conn.commit()

    def bbox_query(self, lon, lat, radius):
        min_lat, min_lon =  inverse_haversine((lat,lon), radius,Direction.SOUTHWEST, Unit.METERS)
        max_lat, max_lon = inverse_haversine((lat,lon), radius,Direction.NORTHEAST, Unit.METERS)

        cursor = self.conn.cursor()
        query = '''
            SELECT ri.*, r.name, r.maxspeed FROM roads_index ri
            JOIN roads r ON ri.road_id = r.id
                WHERE minX < ? AND maxX > ?
                AND minY < ? AND maxY > ?
        '''
        cursor.execute(query, (max_lon, min_lon, max_lat, min_lat))
        bbox = [(min_lat, min_lon), (max_lat, max_lon)]
        return cursor.fetchall(), bbox

    def nearest_road_distance(self, lon, lat, radius=60):
        candidates = self.bbox_query(lon, lat, radius)
        min_dist = None
        nearest = None
        for row in candidates:
            # ri columns: id, minX, maxX, minY, maxY, road_id, startX, startY, endX, endY, name, maxspeed
            dist = point_to_segment_distance(lon, lat, row[6], row[7], row[8], row[9])
            if min_dist is None or dist < min_dist:
                min_dist = dist
                nearest = row
        return min_dist, nearest

    def nearest_road_distances(self, lon, lat, radius=60):
        candidates, bbox = self.bbox_query(lon, lat, radius)
        results = []
        for row in candidates:
            dist, (drawstart, drawend) = point_to_segment_distance(lon, lat, row[6], row[7], row[8], row[9])
            results.append((dist, row, drawstart, drawend))
        results = sorted(results, key=lambda x: x[0])
        print("results:", results)
        return results, bbox
