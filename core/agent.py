"""
SocialAgent — Sequential Chain Orchestrator

Orchestrates the 3-layer engagement pipeline:
  Phase 1: Judge ALL candidates  → batch semantic filter (lightweight LLM)
  Phase 2: Rank by virality      → pick the best post (pure Python)
  Phase 3: ContextBuilder        → assemble RAG, dossier, signals (pure Python)
  Phase 4: Ghostwriter           → generate the comment (full persona LLM)
"""
from typing import Optional, List, Tuple
from config.settings import settings
from core.logger import logger, NetBotLoggerAdapter
from core.models import SocialPost, ActionDecision
from core.knowledge_base import NetBotKnowledgeBase
from core.profile_analyzer import ProfileAnalyzer
from core.chains.judge import Judge, JudgeVerdict
from core.chains.context_builder import ContextBuilder
from core.chains.ghostwriter import Ghostwriter


class SocialAgent:
    def __init__(self):
        self.logger = NetBotLoggerAdapter(logger, {'stage': 'C', 'status_code': 'BRAIN'})
        self.knowledge_base = NetBotKnowledgeBase()

        # Sequential Chain Layers
        self.judge = Judge()
        self.context_builder = ContextBuilder(
            knowledge_base=self.knowledge_base,
            profile_analyzer=ProfileAnalyzer()
        )
        self.ghostwriter = Ghostwriter()

        self.logger.info("🧠 SocialAgent initialized (Pipeline: Judge All → Rank → Write Best)")

    def judge_all(self, candidates: List[SocialPost]) -> List[Tuple[SocialPost, JudgeVerdict]]:
        """
        Phase 1: Pass ALL candidates through the Judge.
        Returns a list of (post, verdict) tuples for approved posts.
        """
        approved = []
        for i, post in enumerate(candidates):
            self.logger.info(f"⚖️ Judging {i+1}/{len(candidates)}: {post.id}")
            try:
                verdict = self.judge.evaluate(post)
                if verdict.should_engage:
                    approved.append((post, verdict))
                    self.logger.info(f"   ✅ Approved ({verdict.category.value}, {verdict.language})")
                else:
                    self.logger.info(f"   ❌ Rejected: {verdict.reasoning}")
                    # Log rejection to discovery
                    from core.database import db
                    db.update_discovery_status(post.id, post.platform.value, "rejected", f"[Judge] {verdict.reasoning}")
            except Exception as e:
                self.logger.error(f"   ⚠️ Judge error for {post.id}: {e}")

        self.logger.info(f"📊 Judge Results: {len(approved)}/{len(candidates)} approved")
        return approved

    def rank_by_virality(self, approved: List[Tuple[SocialPost, JudgeVerdict]]) -> List[Tuple[SocialPost, JudgeVerdict]]:
        """
        Phase 2: Rank approved posts by virality potential.
        Score = likes + (comments * 3) + (shares * 5) + views * 0.01
        Higher engagement = higher chance of our comment being seen.
        """
        def virality_score(item: Tuple[SocialPost, JudgeVerdict]) -> float:
            post = item[0]
            likes = post.like_count or 0
            comments = post.comment_count or 0
            shares = post.share_count or 0
            views = post.metrics.get('view_count', 0) or post.metrics.get('views', 0) or 0
            followers = post.metrics.get('follower_count', 0) or 0

            score = likes + (comments * 3) + (shares * 5) + (views * 0.01) + (followers * 0.001)
            return score

        ranked = sorted(approved, key=virality_score, reverse=True)

        # Log the ranking
        for i, (post, verdict) in enumerate(ranked):
            score = virality_score((post, verdict))
            self.logger.info(
                f"   #{i+1} {post.id} | Score: {score:.1f} | "
                f"❤️{post.like_count} 💬{post.comment_count} 🔄{post.share_count} | "
                f"@{post.author.username}"
            )

        return ranked

    def decide_and_comment(self, post: SocialPost, verdict: JudgeVerdict, client=None) -> ActionDecision:
        """
        Phase 3+4: Build context and generate comment for a SINGLE pre-approved post.

        Args:
            post: The chosen post (already approved by Judge).
            verdict: The Judge's verdict for this post.
            client: Optional platform client (used by ContextBuilder for profile dossier).

        Returns:
            ActionDecision with the final decision and comment.
        """
        try:
            # ━━━ PHASE 3: CONTEXT BUILDER ━━━
            self.logger.info(f"━━━ Context Builder ━━━ Post {post.id}")
            context = self.context_builder.build(post, verdict, client=client)

            # ━━━ PHASE 4: THE GHOSTWRITER ━━━
            self.logger.info(f"━━━ Ghostwriter ━━━ Post {post.id}")
            output = self.ghostwriter.write(context)

            # ━━━ POST-PROCESSING ━━━
            should_act = True

            # Confidence filter
            if output.confidence_score < 70:
                self.logger.warning(f"⚠️ Confidence too low ({output.confidence_score}%). Skipping.")
                should_act = False
                output.reasoning = f"[Low Confidence {output.confidence_score}%] {output.reasoning}"

            # Empty comment guard
            if not output.comment_text.strip():
                self.logger.warning("⚠️ Empty comment generated. Skipping.")
                should_act = False
                output.reasoning = f"[Empty Comment] {output.reasoning}"

            self.logger.info(
                f"🎯 Final Decision: Act={should_act} | "
                f"Conf={output.confidence_score}% | "
                f"Category={verdict.category.value} | "
                f"Lang={verdict.language}"
            )

            return ActionDecision(
                should_act=should_act,
                confidence_score=output.confidence_score,
                content=output.comment_text,
                reasoning=output.reasoning,
                action_type="comment",
                platform=post.platform
            )

        except Exception as e:
            self.logger.error(f"Agent Malfunction: {e}")
            return ActionDecision(should_act=False, reasoning=f"Error: {e}")
