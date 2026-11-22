"""v1.2 rules: real anonymous ballots, limited reviews and void attempts."""
from __future__ import annotations

import json
import random
from collections import Counter
import pytest

from pretend2paint.core.part_b import (
    RuleError, RoundProgress, RoundStatus, VoteStatus, WordCard, is_correct_guess,
    ScoreRules, GameConfig, choose_spy, build_anonymity_map, decode_public_votes,
    PublicDrawing, AuthorRecord, ReviewerRecord, ModerationLedger, review_round,
    review_vote_quota, review_threshold, settle_round, RoundOutcome,
    tally_votes, resolve_vote, score_round, apply_scores,
)

PEOPLE=("p1","p2","p3","p4","p5")
SPY="p5"
AUTHORS={f"drawing{i}":pid for i,pid in enumerate(PEOPLE,1)}
ORDER=tuple(AUTHORS)
CIVILIANS=PEOPLE[:-1]
REF="drawing1"


def review(votes=None,ledger=None,*,rng_seed=20,people=PEOPLE,spy=SPY,drawings=AUTHORS,order=ORDER):
    return review_round(
        players=people, spy=spy, drawing_authors=drawings,review_order=order,
        votes=votes if votes is not None else {},
        ledger=ledger if ledger is not None else ModerationLedger(),
        rng=random.Random(rng_seed),
    )


def outcome(votes=None,guess=False,*,spy=SPY,marked="p1",players=PEOPLE):
    votes = votes if votes is not None else {"p2":"p5","p3":"p5","p4":"p5"}
    return RoundOutcome(players,spy,votes,resolve_vote(tally_votes(votes),spy),guess,marked=marked)


def test_weights_disfavor_frequent_spy_but_never_remove_them():
    rng=random.Random(41)
    hist={"p1":4}
    counts=Counter(choose_spy(PEOPLE,rng,hist) for _ in range(10000))
    assert counts['p1'] > 0
    assert counts['p1'] < counts['p2']/12
    assert set(counts) == set(PEOPLE)


@pytest.mark.parametrize('history',[{'ghost':1},{'p1':-1},{'p2':1.5},{'p1':True}])
def test_bad_spy_history_rejected(history):
    with pytest.raises(RuleError):
        choose_spy(PEOPLE,random.Random(3),history)


def test_anonymity_random_deterministic_and_independent_mappings():
    first=build_anonymity_map(PEOPLE,AUTHORS,random.Random(2))
    second=build_anonymity_map(PEOPLE,AUTHORS,random.Random(2))
    assert first == second
    assert set(first.player_labels.values()) == {f'P{i}' for i in range(1,6)}
    assert set(first.drawing_labels.values()) == {f'D{i}' for i in range(1,6)}
    assert first.drawing_labels['drawing1'] != first.player_labels['p1'].replace('P','D')
    assert first.public_gallery('drawing1') == tuple(
        PublicDrawing(f'D{i}',first.drawing_labels['drawing1']==f'D{i}') for i in range(1,6)
    )
    labels=first.public_review_order(random.Random(100))
    assert len(labels)==5 and set(labels)==set(first.drawing_labels.values())
    assert all(not hasattr(draw, 'author') for draw in first.public_gallery())


def test_public_ballot_is_mapped_on_trusted_referee():
    ids=build_anonymity_map(PEOPLE,AUTHORS,random.Random(10))
    target_label=ids.drawing_labels['drawing5']
    assert decode_public_votes({'p2':target_label},ids)=={'p2':SPY}
    with pytest.raises(RuleError):
        decode_public_votes({'p2':'D999'},ids)


@pytest.mark.parametrize('n,quota,threshold',[(4,1,2),(5,1,3),(6,2,4),(7,2,4)])
def test_quota_threshold(n,quota,threshold):
    assert review_vote_quota(n)==quota
    assert review_threshold(n)==threshold


def test_review_no_clicks_defaults_to_no_violation():
    r=review()
    assert r.flagged_drawings==frozenset()
    assert all(p==0 for p in r.penalty_delta.values())
    assert len(r.reviewer_eligible_this_attempt)==4


def test_self_review_is_allowed_and_does_not_leak_author():
    r=review({'p1':['drawing1'],'p2':['drawing1'],'p3':['drawing1']})
    assert r.flagged_drawings=={'drawing1'}
    assert r.penalty_delta['p1']==-15
    assert r.ledger.authors['p1'].confirmed_violations==1
    assert r.may_show_to_spy_before_guess('drawing1') is False
    assert r.may_show_to_spy_before_guess('drawing2') is True


def test_second_author_violation_removes_without_double_first_penalty():
    r1=review({'p1':['drawing2'],'p2':['drawing2'],'p3':['drawing2']})
    r2=review({'p1':['drawing2'],'p2':['drawing2'],'p4':['drawing2']},r1.ledger)
    assert r1.penalty_delta['p2']==-15
    assert r2.ledger.authors['p2'].confirmed_violations==2
    assert r2.removed_players=={'p2'}
    assert r2.penalty_delta['p2']==0


def test_civilian_cannot_spend_beyond_review_quota():
    with pytest.raises(RuleError):
        review({'p1':['drawing1','drawing2']})


def test_review_duplicate_drawings_and_unknown_drawing_rejected():
    for choices in (['drawing1','drawing1'],['fake']):
        with pytest.raises(RuleError):
            review({'p1':choices})


def test_spy_review_packet_rejected():
    with pytest.raises(RuleError):
        review({'p5':['drawing1']})


def test_reviewer_failures_punish_separately_from_author_violations():
    ledger=ModerationLedger()
    penalties=[]
    for i in range(4):
        r=review({'p2':['drawing1']},ledger)
        penalties.append(r.penalty_delta['p2'])
        ledger=r.ledger
    assert penalties==[0,0,-3,-6]
    assert ledger.reviewers['p2'].failure_streak==0
    assert ledger.reviewers['p2'].pending_suspensions==1
    assert ledger.authors['p2'].confirmed_violations==0


def test_successful_review_resets_failure_streak():
    r1=review({'p2':['drawing1']})
    assert r1.ledger.reviewers['p2'].failure_streak==1
    r2=review({'p1':['drawing1'],'p2':['drawing1'],'p3':['drawing1']},r1.ledger)
    assert r2.ledger.reviewers['p2'].failure_streak==0


def test_suspension_cannot_make_fixed_threshold_unreachable():
    ledger=ModerationLedger(reviewers={p:ReviewerRecord(pending_suspensions=1) for p in CIVILIANS})
    r=review({},ledger)
    assert len(r.reviewer_suspended_this_attempt)==1 # 4 civilians, fixed threshold 3
    assert len(r.reviewer_eligible_this_attempt)==3
    assert sum(x.pending_suspensions for x in r.ledger.reviewers.values())==3


def test_suspended_reviewer_packets_rejected():
    ledger=ModerationLedger(reviewers={'p1':ReviewerRecord(pending_suspensions=1)})
    with pytest.raises(RuleError):
        review({'p1':['drawing2']},ledger)


def test_review_quota_bounds_all_flagged_drawings_without_extra_hide_cap():
    for n in range(4,8):
        players=tuple(f'p{i}' for i in range(n))
        drawings={f'd{i}':p for i,p in enumerate(players)}
        rng=random.Random(n)
        limit=review_vote_quota(n)
        threshold=review_threshold(n)
        # Most adversarial: every civilian uses full quota on rotated choices.
        all_votes={p:tuple(list(drawings)[j%len(drawings)] for j in range(k*limit,k*limit+limit))
                   for k,p in enumerate(players[:-1])}
        r=review_round(players=players,spy=players[-1],drawing_authors=drawings,
                       review_order=tuple(drawings),votes=all_votes,
                       ledger=ModerationLedger(),rng=rng)
        assert len(r.flagged_drawings) <= ((n-1)*limit)//threshold


def test_flagged_reference_void_without_normal_scores_or_history():
    r=review({'p1':['drawing1'],'p2':['drawing1'],'p3':['drawing1']})
    progress=RoundProgress(target_rounds=2).begin_attempt()
    settled=settle_round(progress=progress,review=r,reference_drawing_id=REF,
                         drawing_authors=AUTHORS,players=PEOPLE,spy=SPY,
                         spy_history={'p5':1},rules=ScoreRules())
    assert settled.status is RoundStatus.VOID_REFERENCE_VIOLATION
    assert settled.normal_delta == {p:0 for p in PEOPLE}
    assert settled.disciplinary_delta['p1']==-15
    assert settled.total_delta['p1']==-15
    assert settled.progress.completed_rounds==0
    assert settled.progress.attempts_started==1
    assert settled.progress.attempts_settled==1
    assert settled.spy_history['p5']==1
    next_progress=settled.progress.begin_attempt()
    assert next_progress.current_attempt_id==2


def test_void_rejects_guess_or_vote_outcome_to_prevent_double_scoring():
    r=review({'p1':['drawing1'],'p2':['drawing1'],'p3':['drawing1']})
    with pytest.raises(RuleError):
        settle_round(progress=RoundProgress(2).begin_attempt(),review=r,
                     reference_drawing_id=REF,drawing_authors=AUTHORS,
                     players=PEOPLE,spy=SPY,spy_history={},rules=ScoreRules(),
                     outcome=outcome())


def test_nonreference_violation_does_not_void_and_remains_votable():
    r=review({'p1':['drawing2'],'p2':['drawing2'],'p3':['drawing2']})
    ballot={'p2':'p5','p3':'p5','p4':'p5','p1':'p5'}
    settled=settle_round(progress=RoundProgress(2).begin_attempt(),review=r,
                         reference_drawing_id=REF,drawing_authors=AUTHORS,players=PEOPLE,
                         spy=SPY,spy_history={},rules=ScoreRules(),
                         outcome=outcome(ballot,False))
    assert settled.status is RoundStatus.SCORED
    assert settled.normal_delta['p5']==-3
    assert settled.total_delta['p2']==-4  # +11 correct vote -15 author violation
    assert settled.progress.completed_rounds==1
    assert settled.spy_history=={'p5':1}
    assert settled.removed_players==frozenset()


def test_spy_drawing_flagged_does_not_void_or_make_spy_immune():
    r=review({'p1':['drawing5'],'p2':['drawing5'],'p3':['drawing5']})
    settled=settle_round(progress=RoundProgress(2).begin_attempt(),review=r,
                         reference_drawing_id=REF,drawing_authors=AUTHORS,players=PEOPLE,
                         spy=SPY,spy_history={},rules=ScoreRules(),
                         outcome=outcome())
    assert settled.status is RoundStatus.SCORED
    assert settled.normal_delta['p5']==-3
    assert settled.disciplinary_delta['p5']==-15
    assert settled.total_delta['p5']==-18


def test_unique_innocent_top_means_escape_without_spy_guess():
    votes={'p1':'p3','p2':'p3','p3':'p5','p4':'p3'}
    rr=outcome(votes,guess=None)
    assert rr.vote.status(SPY) is VoteStatus.SPY_ESCAPED
    assert score_round(rr,ScoreRules())['p5']==3


def test_tie_and_abstention_guess_neutral_if_wrong():
    votes={'p1':'p5','p2':'p4','p3':'p4','p4':'p5'}
    tie=outcome(votes,guess=False)
    assert tie.vote.status(SPY) is VoteStatus.TIE
    assert score_round(tie,ScoreRules())['p5']==0
    assert score_round(outcome({},guess=False),ScoreRules())['p5']==0
    assert score_round(outcome({},guess=True),ScoreRules())['p5']==1


def test_spy_cannot_vote_and_own_vote_never_gets_bonus():
    votes={'p5':'p5','p2':'p5'}
    with pytest.raises(RuleError):
        score_round(outcome(votes,False),ScoreRules())


def test_completed_round_and_void_round_counter_separation():
    r=review()
    progress=RoundProgress(2).begin_attempt()
    for attempt in range(2):
        settled=settle_round(progress=progress,review=r,
                             reference_drawing_id=REF,drawing_authors=AUTHORS,
                             players=PEOPLE,spy=SPY,spy_history={},rules=ScoreRules(),
                             outcome=outcome())
        progress=settled.progress
        assert progress.completed_rounds==attempt+1
        if attempt==0:
            progress=progress.begin_attempt()
    with pytest.raises(RuleError):
        progress.begin_attempt()
    with pytest.raises(RuleError):
        settle_round(progress=progress,review=r,
                     reference_drawing_id=REF,drawing_authors=AUTHORS,
                     players=PEOPLE,spy=SPY,spy_history={},rules=ScoreRules(),
                     outcome=outcome())


def test_valid_config_serializes_new_fields():
    cfg=GameConfig()
    assert cfg.validate()==[]
    data=json.loads(json.dumps(cfg.to_payload()))
    assert GameConfig.from_payload(data)==cfg
    assert cfg.phase_seconds[next(p for p in cfg.phase_seconds if p.value=='REVIEW')]==5


def test_same_result_independent_of_private_player_labels():
    votes={"p1":"p5","p2":"p5","p3":"p5","p4":"p5"}
    expected=score_round(outcome(votes,False),ScoreRules())
    for seed in (1,11,77):
        ids=build_anonymity_map(PEOPLE,AUTHORS,random.Random(seed))
        label=ids.drawing_labels['drawing5']
        internal=decode_public_votes({p:label for p in CIVILIANS},ids)
        assert score_round(outcome(internal,False),ScoreRules())==expected


def test_active_roster_can_prune_removed_players_without_reusing_old_records():
    from pretend2paint.core.part_b import restrict_ledger
    old=ModerationLedger(authors={'p2':AuthorRecord(2,0),'p1':AuthorRecord(1,0)},
                         reviewers={'p2':ReviewerRecord(3,1),'p4':ReviewerRecord(1,0)})
    new=restrict_ledger(old,('p1','p3','p4','p5'))
    assert set(new.authors)=={'p1'}
    assert set(new.reviewers)=={'p4'}
    assert 'p2' in old.authors


def test_review_attempt_id_blocks_replayed_result():
    r=review_round(players=PEOPLE,spy=SPY,drawing_authors=AUTHORS,
                   review_order=ORDER,votes={},ledger=ModerationLedger(),
                   rng=random.Random(5),attempt_id=8)
    assert r.attempt_id==8
    with pytest.raises(RuleError):
        settle_round(progress=RoundProgress(2).begin_attempt(),review=r,
                     reference_drawing_id=REF,drawing_authors=AUTHORS,
                     players=PEOPLE,spy=SPY,spy_history={},rules=ScoreRules(),
                     outcome=outcome())


def test_review_attempt_id_rejects_bad_types():
    for invalid in (-1,0,True,'1'):
        with pytest.raises(RuleError):
            review_round(players=PEOPLE,spy=SPY,drawing_authors=AUTHORS,
                         review_order=ORDER,votes={},ledger=ModerationLedger(),
                         rng=random.Random(5),attempt_id=invalid)


def test_competition_rank_and_winners_are_true_ties():
    from pretend2paint.core.part_b import rank_with_ties, winners
    board={'p4':4,'p3':8,'p1':8,'p2':3}
    assert rank_with_ties(board)==[
        ('p1',8,1),('p3',8,1),('p4',4,3),('p2',3,4)
    ]
    assert winners(board)==('p1','p3')
    assert winners({})==()
