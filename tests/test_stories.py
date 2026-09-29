
import copy
import json
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import mock

from src.stories import (
    STORIES_PATH,
    StoryError,
    load_stories,
    story_summary,
    validate_story,
)


def valid_story():
    return {
        "id": "test-story",
        "category": "Incendio",
        "title": "Titolo",
        "place": "Luogo",
        "country": "Italia",
        "latitude": 40.0,
        "longitude": 9.0,
        "side_km": 5,
        "event_date": "2021-07-24",
        "summary": "Sintesi.",
        "what_to_look": "Cosa osservare.",
        "caveat": "Limiti.",
        "facts": ["Fatto"],
        "sources": [{"title": "Fonte", "url": "https://example.org"}],
        "before": {"start": "2021-07-01", "end": "2021-07-23", "target": "2021-07-20"},
        "after": {"start": "2021-08-01", "end": "2021-08-31", "target": "2021-08-10"},
    }


class TestStoriesFile(unittest.TestCase):
    """Il file reale data/stories.json deve essere sempre valido."""

    def test_real_file_is_valid(self):
        stories = load_stories()
        self.assertGreaterEqual(len(stories), 5)

    def test_real_file_has_sources_with_urls(self):
        with STORIES_PATH.open(encoding="utf-8") as file:
            data = json.load(file)
        for story in data["stories"]:
            with self.subTest(story=story["id"]):
                for source in story["sources"]:
                    self.assertTrue(source["url"].startswith("https://"))


class TestValidation(unittest.TestCase):

    def test_valid_story_dates_are_parsed(self):
        story = validate_story(valid_story())
        self.assertEqual(story["event_date"], date(2021, 7, 24))
        self.assertEqual(story["before"]["target"], date(2021, 7, 20))
        self.assertEqual(story["min_valid_percentage"], 85.0)

    def test_before_window_must_end_before_event(self):
        story = valid_story()
        story["before"]["end"] = "2021-07-25"
        with self.assertRaises(StoryError):
            validate_story(story)

    def test_target_inside_window(self):
        story = valid_story()
        story["after"]["target"] = "2021-09-15"
        with self.assertRaises(StoryError):
            validate_story(story)

    def test_sources_required(self):
        story = valid_story()
        story["sources"] = []
        with self.assertRaises(StoryError):
            validate_story(story)

    def test_side_limit(self):
        story = valid_story()
        story["side_km"] = 50
        with self.assertRaises(StoryError):
            validate_story(story)

    def test_summary_fields(self):
        summary = story_summary(validate_story(valid_story()))
        self.assertEqual(summary["event_date"], "2021-07-24")
        self.assertNotIn("before", summary)


class TestStoryEndpoints(unittest.TestCase):

    def setUp(self):
        import api.main as api
        self.api = api
        api._STORY_SCENES_CACHE.clear()
        api._ITEM_CACHE.clear()

    def fake_item(self, item_id, day):
        return SimpleNamespace(
            id=item_id,
            datetime=datetime.fromisoformat(day).replace(tzinfo=timezone.utc),
            properties={"eo:cloud_cover": 2.0},
            assets={},
        )

    def test_list_stories(self):
        result = self.api.list_stories()
        self.assertEqual(result["count"], len(result["stories"]))
        self.assertIn("montiferru-2021", [s["id"] for s in result["stories"]])

    def test_get_story_uses_windows_and_caches(self):
        calls = []

        def fake_find(bbox, start, end, target, max_candidates=6, min_valid=95.0):
            calls.append((start, end, target, min_valid))
            item = self.fake_item(f"S2_{target.isoformat()}", target.isoformat())
            return (item, 97.5), 3, 3

        # Copia delle storie senza scene fissate: si verifica la ricerca.
        unpinned = copy.deepcopy(load_stories())
        for story in unpinned:
            story.pop("before_item_id", None)
            story.pop("after_item_id", None)

        with mock.patch.object(self.api, "find_clear_scene", fake_find), \
                mock.patch.object(self.api, "load_stories", lambda: unpinned):
            result = self.api.get_story("montiferru-2021")
            again = self.api.get_story("montiferru-2021")

        # Una sola ricerca per finestra: la seconda chiamata usa la cache.
        self.assertEqual(len(calls), 2)
        self.assertIs(result, again)

        story = {s["id"]: s for s in load_stories()}["montiferru-2021"]
        self.assertEqual(result["before"]["date"], story["before"]["target"].isoformat())
        self.assertEqual(result["after"]["date"], story["after"]["target"].isoformat())
        self.assertIn("kind=diff", result["after"]["images"]["diff"])
        self.assertIn(f"side_km={float(story['side_km'])}", result["after"]["images"]["rgb"])
        self.assertEqual(calls[0][3], story["min_valid_percentage"])
        self.assertIn("2021", result["attribution"])

    def test_pinned_items_skip_search(self):
        import src.stories as stories_module

        original = stories_module.load_stories()
        pinned = copy.deepcopy(original)
        for story in pinned:
            if story["id"] == "pergusa-2024":
                story["before_item_id"] = "S2_PINNED_BEFORE"
                story["after_item_id"] = "S2_PINNED_AFTER"

        items = {
            "S2_PINNED_BEFORE": self.fake_item("S2_PINNED_BEFORE", "2022-07-10"),
            "S2_PINNED_AFTER": self.fake_item("S2_PINNED_AFTER", "2024-07-12"),
        }

        with mock.patch.object(self.api, "load_stories", lambda: pinned), \
                mock.patch.object(self.api, "get_item_by_id", items.get), \
                mock.patch.object(self.api, "find_clear_scene",
                                  side_effect=AssertionError("non deve cercare")):
            result = self.api.get_story("pergusa-2024")

        self.assertEqual(result["before"]["item_id"], "S2_PINNED_BEFORE")
        self.assertIsNone(result["before"]["valid_percentage"])

    def test_unknown_story(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.api.get_story("non-esiste")
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
