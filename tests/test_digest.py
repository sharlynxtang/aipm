import json
import os
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from ai_digest.cli import main
from ai_digest.core import Source, canonical_url, classify, load_sources, parse_feed, select_items
from ai_digest.feishu import send_card, webhook_url
from ai_digest.report import render_report
from ai_digest.summarize import SummaryError, _validate, summarize_items


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 8, 2, 0, tzinfo=timezone.utc)


class FeedTests(unittest.TestCase):
    def test_rss_atom_ranking_and_report(self):
        news = Source("sample_news", "中国新闻", "news", "CN", "https://example.com/news.xml")
        paper = Source("sample_paper", "论文", "paper", "GLOBAL", "https://example.com/papers.xml")
        items = parse_feed((FIXTURES / "sample_news.xml").read_bytes(), news)
        items += parse_feed((FIXTURES / "sample_paper.xml").read_bytes(), paper)
        chosen = select_items(items + items, NOW)
        self.assertEqual(len(chosen), 2)
        self.assertEqual({item.source.category for item in chosen}, {"news", "paper"})
        report = render_report(chosen, NOW, 2, 2, [])
        self.assertIn("中国科技新闻", report)
        self.assertIn("论文", report)
        self.assertIn("产品关注", report)
        self.assertIn("战略关注", report)
        self.assertNotIn("utm_source", canonical_url(items[0].url))

    def test_old_undated_and_future_items_are_excluded(self):
        source = Source("x", "X", "news", "GLOBAL", "https://example.com")
        xml = b'<rss><channel><item><title>Model launch</title><link>https://example.com/old</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate></item><item><title>Undated</title><link>https://example.com/no-date</link></item><item><title>Future</title><link>https://example.com/future</link><pubDate>Sat, 10 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(select_items(parse_feed(xml, source), NOW), [])

    def test_unrelated_general_news_is_excluded(self):
        source = Source("x", "X", "news", "GLOBAL", "https://example.com")
        xml = b'<rss><channel><item><title>Restaurant chain raises funding</title><link>https://example.com/food</link><pubDate>Thu, 08 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(select_items(parse_feed(xml, source), NOW), [])

    def test_open_source_releases_are_selected_but_capped(self):
        source = Source("vllm", "vLLM", "release", "GLOBAL", "https://github.com/example/vllm/releases.atom")
        release = parse_feed((FIXTURES / "sample_release.xml").read_bytes(), source)[0]
        self.assertEqual(release.guid, "tag:github.com,2008:Repository/1/v0.10.0")
        self.assertIn("开源与生态", release.signals)
        releases = [replace(release, source=replace(source, id=f"project{i}"), title=f"Release {i}", url=f"https://example.com/release/{i}", guid=f"release-{i}") for i in range(5)]
        selected = select_items(releases, NOW, limit=10)
        self.assertEqual(len(selected), 3)
        self.assertIn("开源生态发布", render_report(selected, NOW, 1, 1, []))

    def test_feed_guid_deduplicates_changed_release_url(self):
        source = Source("vllm", "vLLM", "release", "GLOBAL", "https://github.com/example/vllm/releases.atom")
        release = parse_feed((FIXTURES / "sample_release.xml").read_bytes(), source)[0]
        revised = replace(release, title="Revised release title", url="https://example.com/another-link", score=release.score + 1)
        self.assertEqual(len(select_items([release, revised], NOW)), 1)

    def test_release_prereleases_and_same_project_noise_are_filtered(self):
        source = Source("vllm", "vLLM", "release", "GLOBAL", "https://github.com/example/vllm/releases.atom")
        stable = parse_feed((FIXTURES / "sample_release.xml").read_bytes(), source)[0]
        candidate = replace(stable, title="v0.10.1rc0", url="https://example.com/rc", guid="rc")
        later_stable = replace(stable, title="v0.10.2", url="https://example.com/stable", guid="stable", score=stable.score + 1)
        chosen = select_items([stable, candidate, later_stable], NOW)
        self.assertEqual([item.title for item in chosen], ["v0.10.2"])

    def test_generic_model_mentions_are_not_evaluation_signals(self):
        signals, _ = classify("New AI model launch", "The model is available.", "official")
        self.assertNotIn("评测与训练", signals)

    def test_product_focus_prefers_product_signal_to_high_scoring_paper(self):
        news_source = Source("news", "News", "news", "CN", "https://example.com/news")
        paper_source = Source("paper", "Papers", "paper", "GLOBAL", "https://example.com/papers")
        news = parse_feed((FIXTURES / "sample_news.xml").read_bytes(), news_source)[0]
        paper = replace(parse_feed((FIXTURES / "sample_paper.xml").read_bytes(), paper_source)[0], signals=("评测与训练",), score=20)
        report = render_report([news, paper], NOW, 2, 2, [])
        self.assertIn("**产品关注：**[开源模型推出新的智能体工具]", report)

    def test_config_includes_direct_open_source_release_feeds(self):
        sources = load_sources(Path(__file__).parents[1] / "sources.json")
        release_sources = [source for source in sources if source.category == "release"]
        self.assertEqual(len(release_sources), 4)
        self.assertTrue(all(source.url.endswith("/releases.atom") for source in release_sources))

    def test_cli_fixture_integration(self):
        self.assertEqual(main(["--fixture-dir", str(FIXTURES), "--config", str(FIXTURES / "sources.json"), "--now", NOW.isoformat()]), 0)

    def test_manual_send_pushes_even_when_no_new_items(self):
        with patch("ai_digest.cli.fetch_source", return_value=[]), patch("ai_digest.cli.send_card") as send, patch.dict(os.environ, {"FEISHU_WEBHOOK_TOKEN": "test-token", "DEEPSEEK_API_KEY": "test-model-token"}):
            code = main(["--send", "--config", str(FIXTURES / "sources.json"), "--now", NOW.isoformat()])
        self.assertEqual(code, 0)
        self.assertEqual(send.call_count, 1)
        self.assertIn("没有符合条件的新条目", send.call_args.args[1])

    def test_send_stops_when_any_summary_is_missing(self):
        source = Source("news", "News", "news", "CN", "https://example.com/news")
        item = parse_feed((FIXTURES / "sample_news.xml").read_bytes(), source)[0]
        with patch("ai_digest.cli.fetch_source", return_value=[item]), patch("ai_digest.cli.send_card") as send, patch.dict(os.environ, {"FEISHU_WEBHOOK_TOKEN": "test-token", "DEEPSEEK_API_KEY": "test-model-token"}), patch("ai_digest.cli.summarize_items", side_effect=SummaryError("incomplete")):
            code = main(["--send", "--config", str(FIXTURES / "sources.json"), "--now", NOW.isoformat()])
        self.assertEqual(code, 2)
        send.assert_not_called()

    def test_send_requires_model_key_and_includes_chinese_summary(self):
        source = Source("news", "News", "news", "CN", "https://example.com/news")
        item = parse_feed((FIXTURES / "sample_news.xml").read_bytes(), source)[0]
        args = ["--send", "--config", str(FIXTURES / "sources.json"), "--now", NOW.isoformat()]
        with patch("ai_digest.cli.fetch_source", return_value=[item]), patch("ai_digest.cli.send_card") as send, patch.dict(os.environ, {"FEISHU_WEBHOOK_TOKEN": "test-token"}, clear=True):
            self.assertEqual(main(args), 2)
            send.assert_not_called()
        translated = replace(item, chinese_summary="该资讯介绍开源模型的新智能体工具及其产品集成。")
        with patch("ai_digest.cli.fetch_source", return_value=[item]), patch("ai_digest.cli.summarize_items", return_value=[translated]) as summarize, patch("ai_digest.cli.send_card") as send, patch.dict(os.environ, {"FEISHU_WEBHOOK_TOKEN": "test-token", "DEEPSEEK_API_KEY": "test-model-token"}, clear=True):
            self.assertEqual(main(args), 0)
        summarize.assert_called_once()
        self.assertIn("摘要：该资讯介绍开源模型的新智能体工具及其产品集成。", send.call_args.args[1])

    def test_complete_chinese_summaries_are_rendered_under_each_item(self):
        news = Source("news", "News", "news", "CN", "https://example.com/news")
        paper = Source("paper", "Paper", "paper", "GLOBAL", "https://example.com/paper")
        items = [parse_feed((FIXTURES / name).read_bytes(), source)[0] for name, source in (("sample_news.xml", news), ("sample_paper.xml", paper))]
        translated = [replace(item, chinese_summary=f"这条资讯来自{item.source.name}，详情请查看原文。") for item in items]
        report = render_report(translated, NOW, 2, 2, [], require_summaries=True)
        self.assertEqual(report.count("摘要："), 2)
        self.assertNotIn("来源摘录：", report)
        with self.assertRaises(ValueError):
            render_report(items, NOW, 2, 2, [], require_summaries=True)


class SummaryTests(unittest.TestCase):
    def test_model_response_validation_requires_complete_chinese_rows(self):
        self.assertEqual(_validate({"summaries": [{"id": 1, "summary": "第二条资讯摘要。"}, {"id": 0, "summary": "第一条资讯摘要。"}]}, 2), ["第一条资讯摘要。", "第二条资讯摘要。"])
        for rows in ([{"id": 0, "summary": "Only English"}], [{"id": 0, "summary": "第一条。"}, {"id": 0, "summary": "重复。"}], []):
            with self.assertRaises(SummaryError):
                _validate({"summaries": rows}, 2)

    def test_model_request_sends_only_feed_evidence_and_renders_chinese(self):
        source = Source("paper", "论文", "paper", "GLOBAL", "https://example.com/papers")
        item = parse_feed((FIXTURES / "sample_paper.xml").read_bytes(), source)[0]

        class Handler(BaseHTTPRequestHandler):
            received = None

            def do_POST(self):
                self.__class__.received = {"authorization": self.headers["Authorization"], "body": json.loads(self.rfile.read(int(self.headers["Content-Length"]))) }
                result = {"choices": [{"message": {"content": json.dumps({"summaries": [{"id": 0, "summary": "该论文评测开源权重模型的推理成本。"}]}, ensure_ascii=False)}}]}
                body = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            enriched = summarize_items([item], "test-model-token", endpoint=f"http://127.0.0.1:{server.server_port}/summarize")
            self.assertEqual(enriched[0].chinese_summary, "该论文评测开源权重模型的推理成本。")
            self.assertEqual(Handler.received["authorization"], "Bearer test-model-token")
            evidence = json.loads(Handler.received["body"]["messages"][1]["content"])
            self.assertEqual(evidence[0]["title"], item.title)
            self.assertEqual(evidence[0]["excerpt"], item.summary)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


class _WebhookHandler(BaseHTTPRequestHandler):
    received = None

    def do_POST(self):
        self.__class__.received = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = b'{"code":0,"msg":"success"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class FeishuTests(unittest.TestCase):
    def test_webhook_payload_reaches_http_server(self):
        server = HTTPServer(("127.0.0.1", 0), _WebhookHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            send_card(f"http://127.0.0.1:{server.server_port}/hook", "测试日报")
            self.assertEqual(_WebhookHandler.received["msg_type"], "interactive")
            self.assertIn("测试日报", _WebhookHandler.received["card"]["elements"][0]["text"]["content"])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_token_is_path_segment_only(self):
        self.assertTrue(webhook_url("abc-123").endswith("/abc-123"))
        self.assertTrue(webhook_url("{{secret_placeholder}}").endswith("/{{secret_placeholder}}"))
        with self.assertRaises(ValueError):
            webhook_url("https://example.com/hook/secret")


if __name__ == "__main__":
    unittest.main()
