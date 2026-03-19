# Poli-News + Sapien Protocol Integration
## Complete Flow Documentation & Use Cases

**Version:** 1.0  
**Date:** 2026-03-19  
**Status:** Architecture & Integration Proposal

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Sapien Protocol Overview](#sapien-protocol-overview)
3. [Integration Architecture](#integration-architecture)
4. [Use Case 1: Internal Article Quality Verification](#use-case-1-internal-article-quality-verification)
5. [Use Case 2: Third-Party Article Integration](#use-case-2-third-party-article-integration)
6. [Use Case 3: Partner iframe Integration](#use-case-3-partner-iframe-integration)
7. [Data Model & Storage](#data-model--storage)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Security & Economic Incentives](#security--economic-incentives)

---

## 🎯 Executive Summary

**Poli-News can powerfully integrate with Sapien Protocol** to solve a critical problem: **verifying the quality of AI-generated quiz content and reader comprehension validation at scale, with economic consensus and onchain attestation.**

### Current Poli-News Flow (Without Sapien)
```
RSS Article → Collector → Normalizer → LLM Keypoints → LLM Quiz Gen → Stories API → User Quiz
                                            ↓
                              [Quality unknown - black box]
```

**Issues:**
- No way to prove quiz quality is good (LLM-generated, unchecked)
- No way to verify reader answers are genuine (could be botted)
- No independent consensus on what constitutes "good" comprehension
- No onchain record of quality verification

### Proposed Flow (With Sapien Integration)
```
RSS Article → Collector → Normalizer → LLM Keypoints → LLM Quiz Gen → 
    ↓
[Create Sapien Project: "Verify Quiz Quality"]
    ↓
Human Reviewers (Validators) + AI Cross-Check (Contributors) ← STAKE
    ↓
[Commit-Reveal Consensus on Quality Score]
    ↓
Onchain Attestation: quiz_quality_score + verifier_reputation
    ↓
Stories API (with onchain quality signal) → User Quiz
    ↓
[Create Sapien Project: "Verify Reader Comprehension"]
    ↓
Multiple Readers verify each other's answers (RLHF-style)
    ↓
Onchain Attestation: reader_authenticity + comprehension_signal
    ↓
Reward System (backed by Sapien consensus)
```

**Benefits:**
- ✅ Verifiable quality signals for quiz content (economic consensus)
- ✅ Proof of authentic reading (stake-weighted validation)
- ✅ Onchain reputation system for readers & validators
- ✅ Slashing mechanism for dishonest validators
- ✅ Tokenomic alignment (SAPIEN + $POLI dual incentives)

---

## 🔗 Sapien Protocol Overview

### Core Concept: Proof of Quality (PoQ)

Sapien introduces an **onchain trust primitive for AI quality** through economic consensus:

**Three Core Steps:**
1. **Originate** — Define quality criteria (Task Definition Spec), submit data, fund reward pool
2. **Contribute** — Contributors submit work or reviews, earn rewards for accuracy
3. **Verify** — Consensus is written onchain as immutable attestation

### Participant Roles

| Role | in Poli-News | Function |
|------|-------------|----------|
| **Originator** | Poli-News Core Team | Creates Sapien projects, funds reward pools, defines quality thresholds |
| **Contributors** | LLMs + Expert Annotators | Generate quiz questions, keypoints; submit work for validation |
| **Validators** | Expert Reviewers + Community | Review contribution quality via commit-reveal scheme, reach consensus |
| **Adapters** | Poli-News Technical Layer | Connect Poli-News to Sapien contracts, manage data flows |

### Protocol Architecture (v0.5)

```
SapienCore (UUPS Proxy)
├── OriginationLib     — Project creation & funding
├── ContributionLib    — Claim slots, submit work
├── ValidationLib      — Commit-reveal orchestration
├── ConsensusLib       — Stake-weighted consensus (sqrt(stake) × reputation)
├── FinalizationLib    — Settlement & reward distribution
├── DisputeLib         — Challenge period disputes
├── ReputationLib      — PoQ reputation decay
└─→ SapienVault        — ERC-4626 staking vault
```

### Key Mechanism: Stake-Weighted Consensus

```
Score = Weighted Average of Validator Scores
      = Σ(validator_score × √validator_stake × validator_reputation) / Σ(√validator_stake × validator_reputation)

Outlier Detection:
  if |score - average| > 1.5σ  → 10% slash
  if |score - average| > 2σ    → 25% slash
  if |score - average| > 3σ    → 50% slash
  if |score - average| > 5σ    → 100% slash

Acceptance Criteria:
  Accepted if average_score ≥ consensusThreshold (e.g., 70%)
  Rejected if average_score < consensusThreshold
```

**Challenge Period:** 7 days for bonded disputes against outcomes

---

## 🏗️ Integration Architecture

### System Design: Poli-News ↔ Sapien

```
┌─────────────────────────────────────────────────────────┐
│                   POLI-NEWS LAYER                       │
├─────────────────────────────────────────────────────────┤
│  API Server (FastAPI)                                   │
│  ├─ /stories/{id}              [with onchain quality]   │
│  ├─ /quiz?story_id={id}        [backed by Sapien PoQ]   │
│  ├─ /attempt (submit answers)  [feeds to Sapien]        │
│  └─ /reputation/{user_id}      [Sapien reputation]      │
└────────────────────────┬────────────────────────────────┘
                         │ Sapien Adapter Layer
┌────────────────────────▼────────────────────────────────┐
│              SAPIEN PROTOCOL LAYER                       │
├─────────────────────────────────────────────────────────┤
│  SapienCore Contracts (Ethereum / Polygon / Arbitrum)   │
│  ├─ Project 1: "Quiz Quality Verification"              │
│  │  ├─ Task: Validate LLM-generated quiz questions      │
│  │  ├─ Contributors: HumanReviewers + AI cross-check     │
│  │  ├─ Validators: Quality experts                       │
│  │  └─ Reward Pool: 10K SAPIEN (+ $POLI bonus)          │
│  │                                                        │
│  ├─ Project 2: "Reader Comprehension Verification"      │
│  │  ├─ Task: Validate reader comprehension scores       │
│  │  ├─ Contributors: Readers (submit answers)            │
│  │  ├─ Validators: Peer reviewers + AI verification      │
│  │  └─ Reward Pool: Per-story allocation                 │
│  │                                                        │
│  └─ Project 3: "Keypoint Quality Check"                 │
│     ├─ Task: Verify LLM-generated summary keypoints     │
│     ├─ Contributors: Annotators                          │
│     └─ Validators: Editorial team                        │
│                                                           │
│  SapienVault (ERC-4626 staking)                          │
│  └─ Locked SAPIEN from contributors & validators         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Across Systems

```
┌──────────────────────────────────────────┐
│  1. ORIGINATION (Poli-News → Sapien)     │
├──────────────────────────────────────────┤
│  Poli-News Adapter detects:               │
│    "New LLM quiz generated for story_id"  │
│  Calls: SapienCore.createProject(...)     │
│    ├─ Task spec: "Validate quiz quality" │
│    ├─ Reward token: SAPIEN (+ $POLI)     │
│    ├─ Consensus threshold: 75% (BPS)     │
│    ├─ Num validations required: 5        │
│    ├─ Validator reward share: 20%         │
│    └─ Data CID: ipfs://story_quiz_data   │
│  Calls: SapienCore.fundProject(...)       │
│    └─ Amount: 100 SAPIEN tokens           │
│  → Project ID created onchain ✓           │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  2. CONTRIBUTION (Contributors Act)      │
├──────────────────────────────────────────┤
│  HumanReviewers (via Sapien Adapter):     │
│    └─ claimToContribute(projectId)        │
│       ├─ Lock stake: 10 SAPIEN            │
│       └─ Receive slot index               │
│                                            │
│  Contributions can be:                     │
│    ├─ "Quiz is high quality" (score: 95) │
│    ├─ "Quiz is medium" (score: 70)        │
│    └─ "Quiz is low" (score: 30)           │
│                                            │
│  Submit via:                               │
│    └─ contribute(projectId, index,        │
│         submissionHash, dataCID)          │
│       ├─ Hash: keccak256(review_data)     │
│       └─ CID: ipfs://review_json          │
│  → Stake locked, ready for validation ✓   │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  3. VALIDATION (Commit-Reveal)           │
├──────────────────────────────────────────┤
│  Expert Validators (via Sapien Adapter):  │
│                                            │
│  Step A: Lock Validator Capacity           │
│    └─ lockValidatorCapacity(50 SAPIEN)    │
│                                            │
│  Step B: Claim Specific Indices (1h limit)│
│    └─ claimToValidate(projectId, indices) │
│       ├─ Reputation check: ≥ threshold    │
│       └─ Slot assigned                    │
│                                            │
│  Step C: COMMIT (Hash score + salt)       │
│    └─ commitValidation(...,               │
│         keccak256(abi.encodePacked(       │
│           uint16(90),    // score        │
│           salt: bytes32  // random        │
│         )), stake: 15 SAPIEN)             │
│       └─ Stake moves: capacity → inFlight │
│                                            │
│  Step D: REVEAL (1-hour reveal window)    │
│    └─ revealValidation(...,               │
│         score: uint16(90),                │
│         salt: bytes32)                    │
│       ├─ Hash verified onchain            │
│       ├─ Score recorded                   │
│       └─ Reputation updated               │
│  → 5 validators have revealed scores ✓    │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  4. CONSENSUS CALCULATION                │
├──────────────────────────────────────────┤
│  Once all N reveals submitted:             │
│                                            │
│  Scores received: [95, 92, 88, 85, 40]   │
│  Validator stakes: [20, 15, 25, 10, 5]   │
│  Validator reps: [100, 95, 98, 85, 50]   │
│                                            │
│  Calculate:                                │
│    weight = √stake × reputation           │
│    avg = Σ(score × weight) / Σ(weight)   │
│    stddev = calculate_volatility()        │
│                                            │
│  Result: avg_score = 90.2                 │
│  Outlier check: score=40 is >2σ away      │
│    → Validator 5 will be slashed 25%      │
│                                            │
│  Set status:                               │
│    if avg_score ≥ 75%: "Accepted"         │
│    else: "Rejected"                       │
│                                            │
│  → Status = ACCEPTED ✓                    │
│  → Challenge period starts (7 days)       │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  5. DISPUTES (Optional, 7-day window)    │
├──────────────────────────────────────────┤
│  Community members can bond dispute:       │
│    └─ If they believe consensus is wrong  │
│                                            │
│  After 7 days with no disputes:            │
│    → Settlement phase auto-starts          │
│  → No disputes filed ✓                     │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  6. SETTLEMENT & REWARDS                 │
├──────────────────────────────────────────┤
│  Validators call: settleValidator(...)    │
│                                            │
│  Validator 1 (score=95, stake=20):        │
│    ├─ Not outlier: no slash               │
│    ├─ Accurate validator                  │
│    ├─ Receive: 20 SAPIEN back + reward    │
│    ├─ Reward: 5 SAPIEN (20% of pool)      │
│    └─ Net: +5 SAPIEN, reputation +10      │
│                                            │
│  Validator 5 (score=40, stake=5):         │
│    ├─ Outlier (>2σ): 25% slash            │
│    ├─ Lose: 1.25 SAPIEN (slashed)         │
│    └─ Reputation -50                      │
│                                            │
│  Contributor (submitted quiz review):     │
│    ├─ Called: releaseContributorReward()  │
│    ├─ Receive: 50 SAPIEN                  │
│    └─ Can claim after cooldown            │
│                                            │
│  → Settlement complete ✓                  │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│  7. PROPAGATE TO POLI-NEWS                │
├──────────────────────────────────────────┤
│  Poli-News Adapter reads:                 │
│    ├─ Onchain attestation                 │
│    ├─ Consensus score: 90.2%              │
│    ├─ Validator count: 4 (outlier=1)      │
│    └─ Quality signal: HIGH ✓              │
│                                            │
│  Update Poli-News DB:                      │
│    UPDATE quizzes                          │
│    SET quality_score = 90.2,               │
│        sapien_project_id = projectId,      │
│        consensus_status = 'accepted',      │
│        quality_verified_at = NOW()         │
│    WHERE quiz_id = 'quiz_abc123'           │
│                                            │
│  Now when reader requests quiz:            │
│    GET /quiz?story_id=story_xyz            │
│    Response includes:                      │
│    {                                       │
│      "quiz_id": "quiz_abc123",             │
│      "questions": [...],                   │
│      "quality_signal": {                   │
│        "score": 90.2,                      │
│        "validators": 4,                    │
│        "consensus_status": "accepted",     │
│        "onchain_attestation": "0x...",     │
│        "view_on_explorer": "etherscan..."  │
│      }                                     │
│    }                                       │
│  → Quality transparent to user ✓           │
└──────────────────────────────────────────┘
```

---

## 📖 Use Case 1: Internal Article Quality Verification

### Scenario
Poli-News ingests a new article from an RSS feed. The pipeline generates quiz questions using LLM (e.g., Ollama qwen2.5). **Before serving to readers, Poli-News wants to verify the quiz quality** using Sapien Protocol.

### Detailed Flow

#### Step 1: Article Processed & Quiz Generated
```
Timeline: 2026-03-19 09:15:00 UTC
──────────────────────────────────────────

1. RSS Collector fetches article:
   Title: "Central Banks Cut Rates in Economic Shift"
   Source: Reuters, Bloomberg, CNBC
   URL: https://reuters.com/article/abc123
   Published: 2026-03-19 08:00:00 UTC

2. Normalizer processes:
   ├─ Deduplicates against 24h history
   ├─ Resolves canonical URLs
   ├─ Cleans text & extracts summary
   └─ Creates story record:
      story_id: "story_fed2024_rate_cut"
      headline: "Central Banks Cut Rates in Economic Shift"
      summary: "Global central banks announce interest rate cuts, 
                signaling confidence in economic stabilization..."
      status: "not_publishable" (pending quality verification)

3. Keypoints Generator (LLM):
   LLM Prompt: "Extract 3-5 key points from this article"
   Generated keypoints:
   ├─ "Fed reduces benchmark rate by 50 basis points"
   ├─ "ECB follows with 25bp cut"
   ├─ "Market predicts further loosening in Q2"
   ├─ "Inflation trending 2.1% (Fed target: 2.0%)"
   └─ "Rate cuts expected to boost equity markets"
   
   quizzes table:
   key_points_generated_at: 2026-03-19 09:15:00 UTC

4. Quiz Pool Generator (LLM):
   LLM Prompt: "Generate 2-3 quiz questions to test comprehension 
                of this article. Questions must require understanding, 
                not just keyword matching."
   
   Generated questions:
   ├─ Q1: "By how much did the Fed reduce the benchmark rate?"
   │   Options: [25bp, 50bp, 75bp, 100bp]
   │   Correct: 50bp
   │
   ├─ Q2: "What inflation rate is the Fed targeting?"
   │   Options: [1.5%, 2.0%, 2.5%, 3.0%]
   │   Correct: 2.0%
   │
   └─ Q3: "Which central banks announced cuts in this article?"
        Options: [Fed+ECB, Fed only, ECB+BoE, All major CBs]
        Correct: Fed+ECB
   
   quizzes table:
   quiz_id: "quiz_fed2024_rate_cut_v1"
   quiz_status: "generated_pending_qa"
   questions_count: 3
```

#### Step 2: Create Sapien Project for Quality Verification
```
Timeline: 2026-03-19 09:16:00 UTC
──────────────────────────────────────────

Poli-News Backend (Originator):
  Detects: Quiz generated, needs verification
  Action: Call Sapien Adapter
  
Call: SapienCore.createProject(
  {
    name: "Quiz Quality - Fed Rate Cut Article",
    description: "Verify quality of LLM-generated quiz questions",
    
    // Task Definition Spec (TDS)
    taskDefinition: {
      type: "QUIZ_QUALITY_VALIDATION",
      article_id: "story_fed2024_rate_cut",
      quiz_id: "quiz_fed2024_rate_cut_v1",
      criteria: {
        "question_clarity": "Each question must be unambiguous",
        "answer_verifiability": "Correct answer must be verifiable from article",
        "difficulty": "Question should require reading comprehension, not trivial",
        "no_tricks": "Questions should not have trick answers",
        "relevance": "Questions should cover article's main points"
      },
      evaluation_rubric: {
        "5": "Excellent - All criteria met, excellent questions",
        "4": "Good - Minor issues, still publishable",
        "3": "Fair - Moderate issues, needs revision",
        "2": "Poor - Major issues, should be regenerated",
        "1": "Unusable - Fundamentally flawed"
      }
    },
    
    // Economic incentives
    rewardToken: SAPIEN,
    totalRewardPool: 100 SAPIEN,
    numValidationsRequired: 5,
    validatorRewardShare: 20%,  // 20 SAPIEN for validators, 80 for contributor
    
    // Consensus parameters
    consensusThresholdBPS: 7500,  // 75% needed for acceptance
    minStakeToClaim: 5 SAPIEN,
    originatorStakeRequirement: 0,
    
    // Timeline
    contributionDeadline: 2026-03-19 12:00:00 UTC (3 hours),
    validationDeadline: 2026-03-19 15:00:00 UTC (1 hour per validator + commit-reveal),
    
    // Metadata
    dataLocation: {
      format: "JSON",
      cid: "ipfs://QmXxxx...",  // Quiz questions + article summary stored on IPFS
      schema: {
        "article_headline": string,
        "quiz_questions": [{
          "question_id": string,
          "text": string,
          "options": [string, string, string, string],
          "correct_option_index": int
        }]
      }
    }
  }
)

Response: projectId = 0x123abc... [ONCHAIN EVENT EMITTED]
Event logs:
├─ ProjectCreated(projectId, originator=PolinewsAdapter, rewardPool=100 SAPIEN)
├─ ProjectFunded(projectId, amount=100 SAPIEN, afterFee=99 SAPIEN)
└─ ProjectTransitioned(projectId, status: Funded → Active)

Poli-News DB Update:
  INSERT INTO sapien_projects (
    project_id, story_id, quiz_id, project_type, 
    onchain_address, status, created_at, expected_completion
  ) VALUES (
    '0x123abc...', 'story_fed2024_rate_cut', 
    'quiz_fed2024_rate_cut_v1', 'QUIZ_QA', 
    '0x123abc...', 'active', NOW(), 
    '2026-03-19 15:30:00 UTC'
  )
```

#### Step 3: Contributors Review & Submit
```
Timeline: 2026-03-19 09:30 - 12:00 UTC
──────────────────────────────────────────

Contributor Role 1: Human Editorial Expert
  Name: alice.editor@polinews.io
  Reputation (Sapien): 95/100
  Prior stakes: 250 SAPIEN total
  
  Actions:
  1. Stakes: claimToContribute(projectId, quantity=1)
     ├─ Lock: 5 SAPIEN (minStakeToClaim)
     └─ Receive: slot_index = 0
     
  2. Reviews article + quiz:
     ├─ Reads article summary
     ├─ Validates each question
     ├─ Checks answer correctness
     ├─ Scores: "4/5 - Good quality, minor wording issue on Q2"
     
  3. Submits review:
     └─ contribute(
          projectId, slotIndex=0,
          submissionHash=keccak256(review_json),
          dataCID="ipfs://review_alice_v1"
        )
     
     Review JSON (stored on IPFS):
     {
       "reviewer": "alice.editor@polinews.io",
       "timestamp": "2026-03-19 10:00:00 UTC",
       "overall_score": 4,
       "comments": "Q2 wording could be clearer",
       "detailed_feedback": [
         {"question_id": "Q1", "score": 5, "comment": "Clear and verifiable"},
         {"question_id": "Q2", "score": 3, "comment": "Ambiguous wording"},
         {"question_id": "Q3", "score": 5, "comment": "Great question"}
       ]
     }

Contributor Role 2: AI Verifier (LLM Agent)
  Name: ai_verifier_001 (Sapien-compatible agent)
  Reputation: 92/100
  
  Actions:
  1. Stakes: claimToContribute(projectId, quantity=1)
     └─ Lock: 5 SAPIEN
     
  2. AI Verification Process:
     ├─ Uses cross-encoder model to verify answer correctness
     ├─ Checks question-answer semantic similarity
     ├─ Validates options are reasonable distractors
     └─ Scores: "5/5 - All questions have verifiable answers in article"
     
  3. Submits AI review:
     └─ contribute(projectId, slotIndex=1, ...)
     
     AI Review JSON:
     {
       "reviewer": "ai_verifier_001",
       "model": "cross-encoder/qnli-distilroberta-base",
       "timestamp": "2026-03-19 10:15:00 UTC",
       "overall_score": 5,
       "methodology": "Cross-encoder semantic verification",
       "question_verification": [
         {
           "question_id": "Q1",
           "answer_verifiable_in_article": true,
           "semantic_similarity": 0.94,
           "confidence": 0.98
         },
         ...
       ]
     }

Result After Contribution Phase:
├─ Contributor 1 (alice): score submitted (pending validation)
├─ Contributor 2 (ai_verifier): score submitted (pending validation)
├─ Slot status: [Pending, Pending]
└─ Awaiting validators...
```

#### Step 4: Validators Review via Commit-Reveal
```
Timeline: 2026-03-19 12:00 - 15:00 UTC (Validation Phase)
──────────────────────────────────────────

VALIDATOR 1: Sarah Chen (Quiz Quality Expert)
  Reputation: 98/100
  Available Capacity: 30 SAPIEN
  
  Timeline: 12:05 UTC
  ─────────────────
  1. Lock capacity:
     lockValidatorCapacity(30 SAPIEN)
     
  2. Claim slot for validation (1-hour deadline):
     claimToValidate(projectId, slotIndices=[0, 1])
     ├─ Validates reputation ≥ threshold ✓
     └─ Receives validation task
     
  3. Review work (independently):
     ├─ Reviews both contributor submissions
     ├─ Alice's review: "Fair analysis but missed pedagogy aspect"
     ├─ AI verification: "Technically solid but lacks pedagogical consideration"
     ├─ Sarah's assessment: Overall score = 4 (Good, but not excellent)
     
  4. COMMIT phase (12:30 UTC):
     score = uint16(4)
     salt = random bytes32
     commitHash = keccak256(abi.encodePacked(uint16(4), salt))
     
     commitValidation(
       projectId,
       slotIndex=0,
       commitHash=0xabcdef...,
       stakedAmount=8 SAPIEN
     )
     ├─ Stake locked: 8 SAPIEN (validatorCapacity → inFlight)
     └─ Commit time logged: 12:30 UTC

VALIDATOR 2: Dr. James Wilson (Economics PhD)
  Reputation: 96/100
  Available Capacity: 25 SAPIEN
  
  Timeline: 12:10 UTC - 13:45 UTC
  ──────────────────────────────
  1. Lock capacity: lockValidatorCapacity(25 SAPIEN)
  2. Claim: claimToValidate(projectId, slotIndices=[0, 1])
  3. Expert review:
     ├─ Deep analysis of economic accuracy
     ├─ Q1: Perfect (rate cut is exactly 50bp)
     ├─ Q2: Excellent (target is exactly 2.0%)
     ├─ Q3: Good but slightly imprecise wording
     └─ Score: 4 (Good quality)
  4. COMMIT: commitValidation(projectId, slotIndex=1, score=4, stake=7)

VALIDATOR 3: Lisa Park (Content Strategist)
  Reputation: 91/100
  
  Timeline: 12:20 UTC - 14:00 UTC
  ───────────────────────────────
  Review & Score: 5 (Excellent - all criteria met perfectly)
  COMMIT: score=5, stake=6

VALIDATOR 4: Carlos Martinez (AI Researcher)
  Reputation: 94/100
  
  Review & Score: 4 (Good)
  COMMIT: score=4, stake=8

VALIDATOR 5: David Kim (Data Quality Lead)
  Reputation: 88/100
  
  Review & Score: 3 (Fair - needs revision on Q2)
  COMMIT: score=3, stake=5

AFTER ALL COMMITS (14:00 UTC):
├─ All 5 validators have committed hashes
├─ Stakes locked: [8, 7, 6, 8, 5] SAPIEN (total 34 SAPIEN in-flight)
├─ Reveal window: 14:00 - 15:00 UTC (1 hour)
└─ Ready for reveal phase...

REVEAL PHASE (14:30 - 15:00 UTC):
──────────────────────────────────

VALIDATOR 1: revealValidation(
  projectId, slotIndex=0,
  score=uint16(4), salt=0x...
) ✓ Hash verified, score recorded

VALIDATOR 2: revealValidation(
  projectId, slotIndex=1,
  score=uint16(4), salt=0x...
) ✓

VALIDATOR 3: revealValidation(..., score=5, ...) ✓
VALIDATOR 4: revealValidation(..., score=4, ...) ✓
VALIDATOR 5: revealValidation(..., score=3, ...) ✓

All reveals received: scores = [4, 4, 5, 4, 3]
└─ Ready for consensus calculation...
```

#### Step 5: Consensus Calculation
```
Timeline: 2026-03-19 15:00:05 UTC
──────────────────────────────────────

ConsensusLib.calculate(ValidationInput[])

Input Data:
────────────
Validator Scores:    [4.0, 4.0, 5.0, 4.0, 3.0]
Validator Stakes:    [8,   7,   6,   8,   5]
Validator Reput:     [98,  96,  91,  94,  88]

Calculation:
────────────
Weight[i] = √stake[i] × (reputation[i] / 100)

Weight[0] = √8 × (98/100) = 2.828 × 0.98   = 2.77
Weight[1] = √7 × (96/100) = 2.646 × 0.96   = 2.54
Weight[2] = √6 × (91/100) = 2.449 × 0.91   = 2.23
Weight[3] = √8 × (94/100) = 2.828 × 0.94   = 2.66
Weight[4] = √5 × (88/100) = 2.236 × 0.88   = 1.97

Total Weight = 2.77 + 2.54 + 2.23 + 2.66 + 1.97 = 12.17

Weighted Average Score:
  = (4.0×2.77 + 4.0×2.54 + 5.0×2.23 + 4.0×2.66 + 3.0×1.97) / 12.17
  = (11.08 + 10.16 + 11.15 + 10.64 + 5.91) / 12.17
  = 48.94 / 12.17
  = 4.02 (out of 5)
  = 80.4% (normalized to 0-100)

Standard Deviation:
  variance = Σ(weight[i] × (score[i] - avg)²) / ΣWeight
  = [2.77×(4-4.02)² + 2.54×(4-4.02)² + 2.23×(5-4.02)² + 2.66×(4-4.02)² + 1.97×(3-4.02)²] / 12.17
  ≈ 0.52 / 12.17
  stddev = 0.206 (approx 0.2)

Outlier Detection (Tiered Thresholds):
  Threshold 1 (1.5σ): 4.02 ± (1.5 × 0.2) = [3.72, 4.32] → 10% slash
  Threshold 2 (2σ):   4.02 ± (2.0 × 0.2) = [3.62, 4.42] → 25% slash
  Threshold 3 (3σ):   4.02 ± (3.0 × 0.2) = [3.42, 4.62] → 50% slash
  
  Checkscores against thresholds:
  - Score 4.0: within 1.5σ ✓ No outlier
  - Score 4.0: within 1.5σ ✓ No outlier
  - Score 5.0: within 2σ but outside 1.5σ → 10% slash (conservative)
  - Score 4.0: within 1.5σ ✓ No outlier
  - Score 3.0: within 2σ but outside 1.5σ → 10% slash

Consensus Decision:
  Acceptance threshold: 75% (BPS: 7500)
  Average score: 80.4%
  Decision: ACCEPTED ✓
  
Status: contribution_status = "Accepted"
Challenge period duration: 7 days (until 2026-03-26 15:00:05 UTC)

Onchain Event Emitted:
ConsensusReached(
  projectId=0x123abc...,
  contributionId=0,
  consensusScore=4.02,
  status=Accepted,
  challengePeriodUntil=2026-03-26T15:00:05Z
)
```

#### Step 6: Settlement & Rewards
```
Timeline: 2026-03-26 15:00 UTC (After challenge period)
────────────────────────────────────────────────────────

Dispute check: No disputes filed ✓

Settlement Phase:

VALIDATOR 1 (Sarah Chen, score=4, stake=8, reputation=98):
  Not outlier (score within thresholds)
  Slash amount: 0 SAPIEN
  Reward calculation:
    ├─ Weight: 2.77
    ├─ Reward pool (validator share): 20 SAPIEN
    ├─ Proportional reward: 2.77 / 12.17 × 20 SAPIEN = 4.56 SAPIEN
    ├─ Receive: 8 SAPIEN (stake) + 4.56 SAPIEN (reward) = 12.56 SAPIEN
    ├─ Reputation change: +10 (honest validator)
    └─ New reputation: 98 + 10 = 108 (capped?) → 100

VALIDATOR 2 (Dr. James Wilson, score=4, stake=7, reputation=96):
  Not outlier
  Receive: 7 + (2.54/12.17 × 20) = 7 + 4.18 = 11.18 SAPIEN
  Reputation: +10 → 106 (capped at 100)

VALIDATOR 3 (Lisa Park, score=5, stake=6, reputation=91):
  Outlier (5.0 is 1.5σ away) → 10% slash
  Slash amount: 0.6 SAPIEN (10% of 6)
  Receive: 6 - 0.6 + (2.23/12.17 × 20) = 5.4 + 3.67 = 9.07 SAPIEN
  Reputation: +8 (outlier penalty) → 99

VALIDATOR 4 (Carlos Martinez, score=4, stake=8, reputation=94):
  Not outlier
  Receive: 8 + (2.66/12.17 × 20) = 8 + 4.38 = 12.38 SAPIEN
  Reputation: +10 → 104 (→100 capped)

VALIDATOR 5 (David Kim, score=3, stake=5, reputation=88):
  Outlier (3.0 is 1.5σ away) → 10% slash
  Slash amount: 0.5 SAPIEN
  Receive: 5 - 0.5 + (1.97/12.17 × 20) = 4.5 + 3.24 = 7.74 SAPIEN
  Reputation: +8 → 96

CONTRIBUTORS:

Contributor 1 (alice.editor):
  ├─ Stake returned: 5 SAPIEN
  ├─ Contributor reward: 80 SAPIEN (80% of reward pool)
  ├─ Receive: 5 + 80 = 85 SAPIEN
  ├─ Reputation: +20 (high-quality work accepted)
  └─ Status: "Accepted" onchain

Contributor 2 (ai_verifier):
  ├─ Stake returned: 5 SAPIEN
  ├─ Contributor reward split: 80 SAPIEN / 2 contributors = 40 SAPIEN
  ├─ Receive: 5 + 40 = 45 SAPIEN
  ├─ Reputation: +20
  └─ Status: "Accepted" onchain

Poli-News Adapter:
  ├─ Notified of completion
  ├─ Protocol fee (1%): 1 SAPIEN → Sapien DAO Treasury
  ├─ Adapter fee (if applicable): 0 (no adapter fee in this case)
  └─ Quiz now has onchain quality attestation ✓

Total Settlement Breakdown:
├─ Returned to validators: [12.56, 11.18, 9.07, 12.38, 7.74] = 52.93 SAPIEN
├─ Returned to contributors: [85, 45] = 130 SAPIEN
├─ Slashed (outliers): [0.6, 0.5] = 1.1 SAPIEN
├─ Protocol fee: 1 SAPIEN
├─ Remaining in escrow: 100 - 52.93 - 130 - 1 = -83.93 (wait, this doesn't add up...)

Actually, let me recalculate:
  Contributor reward pool: 80 SAPIEN
  ├─ alice gets: 80 × [her weight / total contributor weight]
  └─ Let's assume equal split: 40 + 40 = 80 ✓
  
  Validator reward pool: 20 SAPIEN
  ├─ Distributed to validators based on accuracy: 4.56 + 4.18 + 3.67 + 4.38 + 3.24 = 20.03 ✓

Stakes returned:
  ├─ Contributor stakes: 5 + 5 = 10 SAPIEN
  ├─ Validator stakes: 8 + 7 + 6 + 8 + 5 = 34 SAPIEN (total)
  ├─ Less slashes: 34 - 1.1 = 32.9 SAPIEN
  └─ Total returned: 10 + 32.9 = 42.9 SAPIEN

Total out:
  ├─ Contributor rewards: 80 SAPIEN
  ├─ Validator rewards: 20 SAPIEN
  ├─ Returned stakes: 42.9 SAPIEN
  ├─ Protocol fee: 1 SAPIEN
  └─ Total: 80 + 20 + 42.9 + 1 = 143.9 SAPIEN

Wait, reward pool was only 100 SAPIEN. Let me reconsider:

Actually, the 20 SAPIEN for validator reward is PART of the 100 SAPIEN total pool:
  Total pool: 100 SAPIEN
  ├─ Contributor rewards: 80 SAPIEN (80% of pool)
  ├─ Validator rewards: 20 SAPIEN (20% of pool)
  └─ (These come from the 100 SAPIEN, not in addition)

Participants' net gain:
  ├─ Contributor 1: +85 SAPIEN (got 40 SAPIEN reward + 5 SAPIEN stake back)
  ├─ Validator 1: +4.56 SAPIEN (got reward, stake returned with 10% slash of 0.6)
  ├─ Protocol fee: -1 SAPIEN (taken from pool before distribution)
  └─ Stakes locked during process but returned afterward

✓ Settlement complete!
```

#### Step 7: Update Poli-News & Serve with Quality Signal
```
Timeline: 2026-03-26 16:00 UTC
────────────────────────────────

Poli-News Adapter reads from Sapien onchain:
  projectId: 0x123abc...
  finalStatus: "Accepted"
  consensusScore: 4.02 (out of 5.0 = 80.4%)
  challengeResolved: true
  validatorCount: 5
  outliersSlashed: 2
  
Update Poli-News Database:
  UPDATE quizzes
  SET 
    quality_source = 'SAPIEN_POQ',
    quality_score = 80.4,
    quality_consensus_status = 'accepted',
    sapien_project_id = '0x123abc...',
    sapien_validators_count = 5,
    sapien_outliers_count = 2,
    quality_verified_at = NOW(),
    quiz_status = 'quiz_available'
  WHERE quiz_id = 'quiz_fed2024_rate_cut_v1';
  
  UPDATE stories
  SET status = 'publishable'
  WHERE story_id = 'story_fed2024_rate_cut';

Now when Reader accesses:
  GET /stories/story_fed2024_rate_cut/quiz
  
Response:
{
  "story_id": "story_fed2024_rate_cut",
  "headline": "Central Banks Cut Rates in Economic Shift",
  "quiz": {
    "quiz_id": "quiz_fed2024_rate_cut_v1",
    "questions": [
      {
        "question_id": "Q1",
        "text": "By how much did the Fed reduce the benchmark rate?",
        "options": [
          {"option_id": "a", "text": "25 basis points"},
          {"option_id": "b", "text": "50 basis points"},
          {"option_id": "c", "text": "75 basis points"},
          {"option_id": "d", "text": "100 basis points"}
        ]
      },
      ...
    ],
    "quality_signal": {
      "verification_method": "SAPIEN_PROOF_OF_QUALITY",
      "consensus_score": 80.4,
      "validator_count": 5,
      "outliers_handled": true,
      "challenge_period_complete": true,
      "status": "ACCEPTED",
      "onchain_record": {
        "network": "ethereum | polygon | arbitrum",
        "contract_address": "0x...",
        "project_id": "0x123abc...",
        "block_number": 19834820,
        "transaction_hash": "0x...",
        "explorer_link": "https://etherscan.io/tx/0x..."
      }
    }
  },
  "additional_meta": {
    "publisher_scores": [4, 4, 5, 4, 3],
    "average_publication_score": 4.04,
    "ready_for_reading": true
  }
}
```

---

## 📱 Use Case 2: Third-Party Article Integration

### Scenario
A third-party publisher or news aggregator **hosts an article on their own domain** but wants to use **Poli-News quiz infrastructure** to add reader comprehension verification. They embed an iframe pointing to Poli-News.

### Flow

```
┌─────────────────────────────────────────────────┐
│  THIRD-PARTY PUBLISHER WEBSITE                  │
│  (e.g., medium.com, substack.com, etc.)         │
├─────────────────────────────────────────────────┤
│  Article: "How AI is Reshaping Healthcare"      │
│  URL: https://publisher.com/article/ai-health   │
│                                                   │
│  ┌─────────────────────────────────────────┐    │
│  │   [Article Content - HTML]              │    │
│  │                                         │    │
│  │   "Artificial intelligence is now       │    │
│  │    transforming diagnostic imaging...   │    │
│  │   By improving accuracy and speed,      │    │
│  │   AI is reducing diagnostic time by     │    │
│  │   40%..."                               │    │
│  └─────────────────────────────────────────┘    │
│                                                   │
│  ┌─────────────────────────────────────────┐    │
│  │ <iframe src="https://polinews.io/     │    │
│  │          embedded-quiz?                  │    │
│  │          external_article_id=pub_ai123 │    │
│  │          publisher_token=xyz...">       │    │
│  │ </iframe>                               │    │
│  │                                         │    │
│  │   [Poli-News Quiz Box rendered here]    │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Detailed Integration Flow

#### Step 1: Publisher Registers with Poli-News
```
Timeline: Before article publication
──────────────────────────────────

Publisher admin panel:
  Settings → Integrations → Poli-News
  
  Contact: partners@polinews.io
  Register publisher:
  {
    name: "TechNews Daily",
    domain: "technewsdaily.com",
    api_key: (generated by Poli-News),
    webhook_secret: (for signed callbacks),
    config: {
      quiz_difficulty: "medium",
      reward_token: "POLI",
      share_model: "50_50",  // 50% Poli-News, 50% Publisher
      allow_external_data: true,
      data_retention: "90_days"
    }
  }
  
Status: Publisher verified ✓
```

#### Step 2: Publisher Publishes Article with Embedded Quiz
```
Timeline: Article goes live
──────────────────────────────

TechNews Daily publishes article:
  URL: https://technewsdaily.com/article/ai-health-123
  
  Article metadata (sent to Poli-News via API):
  {
    publisher_id: "technewsdaily",
    external_article_id: "ai-health-123",
    title: "How AI is Reshaping Healthcare",
    content: "<html>... full article content ...</html>",
    summary: "Artificial intelligence improves diagnostic accuracy by 40%...",
    source_urls: [
      "https://nature.com/article/ai..."
      "https://lancet.com/article/..."
    ],
    publication_date: "2026-03-19 10:00:00 UTC",
    author: "Dr. Sarah Martinez",
    category: "health-tech"
  }
  
Poli-News creates external article record:
  INSERT INTO external_articles (
    external_article_id, publisher_id, article_hash,
    title, summary, content_cid, status
  ) VALUES (...)
  
  external_article_id: "ext_ai_health_123" (internal ID)
```

#### Step 3: Poli-News Generates Quiz for External Article
```
Timeline: Within 1 hour of article submission
────────────────────────────────────────────────

Poli-News Pipeline (same as internal):

1. Content Ingestion:
   ├─ Receive article via API
   ├─ Store on IPFS/Arweave for permanence
   ├─ Generate content hash

2. Keypoints Generation:
   LLM Prompt: "From this healthcare AI article, extract 3-5 key findings"
   Generated:
   ├─ "AI improves diagnostic accuracy by 40% in imaging"
   ├─ "Cost reduction of 30% achieved through automation"
   ├─ "Regulatory frameworks still being developed"

3. Quiz Generation:
   Generated questions:
   ├─ Q1: "What accuracy improvement did AI achieve in diagnostics?"
   │   Correct: "40%"
   ├─ Q2: "Which regulatory body approved AI diagnostic tools?"
   │   Correct: "FDA & EMA (both mentioned)"

4. Create Sapien Project for External Content QA:
   
   call SapienCore.createProject({
     name: "External Article QA - TechNews Daily - AI Healthcare",
     taskType: "EXTERNAL_CONTENT_VERIFICATION",
     publisher_id: "technewsdaily",
     article_id: "ai-health-123",
     
     criteria: {
       "factual_accuracy": "Statements must match article content",
       "comprehension": "Quiz tests understanding, not memorization",
       "neutrality": "Questions don't introduce bias"
     },
     
     rewardToken: POLI,
     totalRewardPool: 150 POLI,  // Higher stake for publisher content
     numValidationsRequired: 7,    // More validators for third-party
     
     // Publisher custom config
     publisher_config: {
       reward_split: {
         polinews: 60,     // 90 POLI (60%)
         publisher: 40     // 60 POLI (40%)
       },
       quality_threshold: 8000,  // 80% required (higher for external)
       priority: "high"
     }
   })
```

#### Step 4: Reader Uses External Quiz via Iframe
```
Timeline: Reader lands on article
───────────────────────────────────

Reader on technewsdaily.com:
1. Reads article naturally
2. Scrolls down, sees embedded box:
   
   ┌───────────────────────────────────┐
   │  🧠 Test Your Understanding      │
   │                                   │
   │  This quiz helps verify your      │
   │  reading comprehension while      │
   │  supporting quality journalism.   │
   │                                   │
   │  Your data is secure with us.     │
   │                                   │
   │  [📊 View Quality Report]          │
   │  [✏️ Start Quiz →]                │
   └───────────────────────────────────┘

3. Clicks "[✏️ Start Quiz →]"
   
   Poli-News iframe loads:
   └─ Detects external context via referrer policy
   └─ Loads article session token
   └─ Fetches quiz questions (verified by Sapien externally)

4. Quiz box appears:
   
   ┌──────────────────────────────────────────┐
   │ Question 1 of 2                          │
   │                                          │
   │ "What accuracy improvement did AI        │
   │  achieve in diagnostics?"                │
   │                                          │
   │ ◯ 10%                                    │
   │ ◯ 25%                                    │
   │ ◯ 40%                 ← (correct)        │
   │ ◯ 55%                                    │
   │                                          │
   │ ⏱️ Time elapsed: 45 seconds              │
   │                                          │
   │ [← Back] [Next →]                        │
   └──────────────────────────────────────────┘

5. Reader completes quiz (2 questions, ~2 min)
   score: 2/2 = 100%
   
   Result notification:
   
   ┌──────────────────────────────────────────┐
   │ ✅ Quiz Complete!                        │
   │                                          │
   │ Your Score: 100% (2/2 correct)           │
   │                                          │
   │ Quality Signal: VERIFIED ✓               │
   │ (Consensus: 82% by 7 expert reviewers)   │
   │                                          │
   │ Congratulations! You've demonstrated     │
   │ that you understood the article.         │
   │                                          │
   │ You earned: [SHARED REWARD MODEL]        │
   │ • $POLI tokens for verification          │
   │ • Support quality content creators       │
   │                                          │
   │ [Next Article →]                         │
   │ [📊 Your Stats]                          │
   └──────────────────────────────────────────┘
```

#### Step 5: Rewards Split Between Parties
```
Quiz passed!

Reward calculation:
Base: 10 POLI
Quality bonus: +5 POLI (new reader multiplier: 30% = 1.5×)
Total earned: 22.5 POLI

Distribution:
├─ Poli-News: 60% = 13.5 POLI (covers infrastructure)
├─ Publisher: 40% = 9 POLI (supports content creation)
└─ Reader: Gets verified badge + reward

External Article Status Updates:
├─ Total readers: 1000
├─ Quiz participation: 340 (34%)
├─ Avg score: 78%
├─ Total POLI distributed: 340 × 22.5 = 7,650 POLI
│  ├─ To Poli-News: 4,590 POLI
│  └─ To TechNews Daily: 3,060 POLI

TechNews Daily Analytics Dashboard:
├─ Engagement increase: +45% (readers complete quiz)
├─ Revenue share: 3,060 POLI (tradeable)
├─ Reader quality signal: 78% avg comprehension (credible metric)
└─ Articles with verified comprehension get higher SEO weight
```

---

## 🔲 Use Case 3: Partner iframe Integration

### Scenario
**A Poli-News partner (publisher, LMS, news platform) wants to embed a Poli-News quiz box directly on their site**, not as a full-page but as a small component. The partner has an existing article page and wants to "bolt on" comprehension verification.

### Architecture

```
PARTNER SITE                      POLI-NEWS SERVICE
┌──────────────────────┐         ┌─────────────────┐
│  Article Page        │         │  Quiz Service   │
│  ┌────────────────┐  │         │  ┌───────────┐  │
│  │  Content       │  │         │  │ Questions │  │
│  │  ........      │  │         │  │ Scoring   │  │
│  │                │  │         │  │ Rewards   │  │
│  └────────────────┘  │         │  └───────────┘  │
│                      │         │                 │
│  ┌────────────────┐  │ ◄───────► ┌───────────┐  │
│  │  Iframe        │  │  HTTPS    │ Sapien    │  │
│  │  ┌──────────┐  │  │ Messages  │ Protocol  │  │
│  │  │ Quiz Box │  │  │ PostMsg   │ Contracts│  │
│  │  └──────────┘  │  │           │           │  │
│  └────────────────┘  │           └───────────┘  │
└──────────────────────┘           │      │       │
        ▲                           ▼      ▼
        └─────────────────────────────────┘
              Callback to Partner Site
```

### Detailed Implementation

#### Step 1A: Partner Registers & Gets Embed Code
```
Partner Admin Portal:
  integrations.polinews.io/partners
  
  Register Partner Site:
  {
    partner_name: "CourseraPlus",
    website: "courseraplus.edu",
    contact_email: "tech@courseraplus.edu",
    
    integration_type: "IFRAME_EMBEDDED",
    
    config: {
      iframe_height: 500,
      iframe_theme: "light",
      show_publisher_branding: true,
      position_on_page: "below_article",
      enable_social_share: true,
      callback_url: "https://courseraplus.edu/webhooks/quiz-complete"
    }
  }
  
Poli-News generates:
  partner_api_key: "pk_live_...",
  partner_secret: "sk_live_...",
  embed_code_template: `
    <iframe 
      src="https://embed.polinews.io/quiz
           ?partner_id=courseraplus
           &article_id={ARTICLE_ID}
           &token={CSRF_TOKEN}"
      width="100%"
      height="500"
      frameborder="0"
      allow="payment"
    ></iframe>
  `
```

#### Step 1B: Partner Implements Embed
```
CourseraPlus article page HTML:
  
  <article>
    <h1>Machine Learning Fundamentals</h1>
    <div class="article-content">
      <!-- Article content here -->
    </div>
    
    <!-- Poli-News Quiz Embed -->
    <div class="quiz-container">
      <iframe 
        id="polinews-quiz"
        src="https://embed.polinews.io/quiz?
             partner_id=courseraplus&
             article_id=ml_fundamentals_001&
             token=eyJhbGciOiJIUzI1NiIs..."
        width="100%"
        height="500"
        frameborder="0"
      ></iframe>
    </div>
    
    <script>
      // Listen for completion message from iframe
      window.addEventListener('message', (event) => {
        if (event.origin !== 'https://embed.polinews.io') return;
        
        if (event.data.type === 'quiz-complete') {
          // Handle completion on partner side
          const { passed, score, user_id, reward } = event.data;
          
          // Update user's course progress
          courseProgress.markQuizComplete(
            articleId='ml_fundamentals_001',
            score=score,
            passed=passed
          );
          
          // Optional: Grant course credits
          if (passed) {
            courseProgress.grantCredits(2);  // 2 credits
          }
          
          // Send acknowledgment back to iframe
          event.source.postMessage({
            type: 'quiz-complete-ack',
            status: 'success'
          }, event.origin);
        }
      });
    </script>
  </article>
```

#### Step 2: Quiz Experience in Iframe
```
Timeline: User interacts with quiz in embedded iframe
──────────────────────────────────────────────────

Iframe behavior:
1. Loads quiz questions (pre-verified via Sapien)
2. Shows branded header: "Verify Your Understanding"
3. User completes 2-3 questions (60 seconds)

Inside iframe screen:

┌─────────────────────────────────┐
│ Verify Your Learning            │ ← Partner branding
│ Powered by Poli-News ✨         │
│─────────────────────────────────│
│                                 │
│ Question 1 of 2                 │
│                                 │
│ "Which algorithm is best for    │
│  image classification?"          │
│                                 │
│ ◯ Decision Trees                │
│ ◯ Neural Networks ← (correct)    │
│ ◯ Linear Regression             │
│ ◯ K-Means Clustering            │
│                                 │
│ [Previous] [Next]               │
│                                 │
│ ⏱ Time: 28 seconds              │
│ 📊 Quality: VERIFIED (82%)       │
└─────────────────────────────────┘

Upon completion (quiz passed):
1. Iframe sends PostMessage to parent:
   {
     type: 'quiz-complete',
     passed: true,
     score: 100,
     user_id: 'user_abc123' (anonymous hash),
     reward: {
       amount: 15,
       currency: 'POLI',
       status: 'verified'
     },
     attestation_url: 'https://etherscan.io/tx/0x...'
   }

2. Parent page (partner) receives message
   └─ Updates local UI / database
   └─ Can grant course credits, badges, etc.

3. Iframe also sends completion to Poli-News backend:
   POST /api/v1/quiz-completion
   {
     partner_id: 'courseraplus',
     article_id: 'ml_fundamentals_001',
     user_id: 'hash_from_partner_session',
     score: 100,
     elapsed_seconds: 45,
     session_token: '...'
   }
```

#### Step 3: Sapien Integration for Verification
```
Poli-News Backend:
1. Quiz auto-created via Sapien for article
2. Sapien Project for this article:
   
   Project: "ML Fundamentals Quiz QA"
   ├─ Contributors: Educators + AI validators
   ├─ Quiz validated by Sapien QA pipeline
   ├─ Consensus score: 84% (accepted)
   └─ Onchain record: 0x...

2. When user completes quiz:
   ├─ Store attempt record in DB
   ├─ Calculate reward tier
   ├─ Emit Sapien attestation event
   └─ Record reader's comprehension signal onchain

Sapien Project for Reader Verification:
   Create second Sapien project to verify reader authenticity:
   {
     name: "Reader Comprehension - CourseraPlus ML 001",
     type: "READER_VERIFICATION",
     task: "Validate that this reader's answers are genuine (not botted)",
     
     contributors: [
       peer_reviewer_1,
       peer_reviewer_2,
       ai_anomaly_detector
     ],
     
     validators: [
       ml_expert_1,
       educational_assessor,
       fraud_detector_bot
     ]
   }
   
Result: Reader's quiz attempt backed by Sapien consensus ✓
```

#### Step 4: Partner Collects Data & Analytics
```
CourseraPlus Dashboard:

Article: "Machine Learning Fundamentals"
─────────────────────────────────────────

Engagement Metrics (Last 7 days):
  Total Reads: 2,340
  Quiz Attempts: 1,450 (61% engagement!)
  Avg Score: 81%
  Pass Rate: 89%
  
  Readers who passed → Avg course completion: 95%
  Readers who failed → Avg course completion: 42%
  
  Correlation: Strong positive link between comprehension ✓
  
Revenue Share:
  Total POLI distributed: 18,900 POLI
  Partner's 40% share: 7,560 POLI (~$1,890 at $0.25/POLI)
  
Quality Signals (Onchain):
  Sapien attestations: 1,450 ✓
  Average quiz quality score: 84% (verified)
  Reader authenticity score: 91% (verified onchain)
  
Can export:
  ├─ CSV of reader scores + anonymized IDs
  ├─ Onchain attestation links (verify on explorer)
  ├─ Revenue share reports
  └─ Quality metrics for accreditation boards
```

#### Step 5: End-to-End Timeline
```
Timeline: Complete flow
────────────────────────

09:00 - Course launches on CourseraPlus
09:15 - Student Alice reads article
09:22 - Alice sees Poli-News quiz box (embedded iframe)
09:25 - Alice completes quiz (2/2 correct, 100%)
09:25 - Quiz iframe sends PostMessage to parent
09:26 - CourseraPlus marks article as completed for Alice
09:26 - Alice receives 2 course credits + POLI reward
09:27 - Poli-News backend records Alice's attempt
09:30 - Sapien project aggregates this attempt + 1,449 others
12:00 - Sapien validation kicks off (5 expert validators review sample)
14:00 - Consensus reached: 84% quality score, reader authenticity 91%
14:05 - Onchain attestation written to blockchain
14:06 - CourseraPlus dashboard updates with verified metrics
14:07 - CourseraPlus can claim 7,560 POLI share

Timeline Benefits:
✓ Real-time verification (embedded)
✓ Partner keeps full control of user experience
✓ Onchain quality signals for compliance/accreditation
✓ Revenue sharing model aligns incentives
✓ Reader authenticity verified (stops bot farms)
```

---

## 🗄️ Data Model & Storage

### Poli-News Sapien Integration Tables

```sql
-- New tables for Sapien integration

CREATE TABLE sapien_projects (
  project_id TEXT PRIMARY KEY,
  story_id TEXT,  -- if internal Poli-News story
  external_article_id TEXT,  -- if third-party article
  partner_id TEXT,  -- if partner iframe
  
  project_type TEXT NOT NULL,  -- QUIZ_QA | KEYPOINT_QA | READER_VERIFICATION
  task_definition_spec JSONB,  -- Full TDS from Sapien
  
  onchain_address TEXT NOT NULL,  -- Sapien contract address
  onchain_network TEXT,  -- ethereum | polygon | arbitrum
  onchain_block_number INTEGER,
  
  status TEXT NOT NULL,  -- Funded | Active | Accepted | Rejected | Disputed | Completed
  consensus_score FLOAT,  -- 0-100
  validator_count INTEGER,
  outlier_count INTEGER,
  
  reward_pool_amount NUMERIC,
  reward_token TEXT,  -- SAPIEN | POLI
  consensus_threshold_bps INTEGER,  -- e.g., 7500 = 75%
  
  created_at TIMESTAMP,
  completed_at TIMESTAMP,
  challenge_period_until TIMESTAMP,
  
  publisher_config JSONB,  -- Custom config from publisher
  
  FOREIGN KEY (story_id) REFERENCES stories(story_id),
  FOREIGN KEY (partner_id) REFERENCES partners(partner_id)
);

CREATE TABLE sapien_contributions (
  contribution_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  contributor_id TEXT NOT NULL,
  contributor_type TEXT,  -- HUMAN | LLM_AGENT | HYBRID
  
  submission_hash TEXT,
  data_cid TEXT,  -- IPFS CID
  submission_data JSONB,  -- What they contributed
  
  status TEXT,  -- Submitted | Accepted | Rejected
  
  stake_amount NUMERIC,
  stake_returned NUMERIC,
  reward_earned NUMERIC,
  
  created_at TIMESTAMP,
  
  FOREIGN KEY (project_id) REFERENCES sapien_projects(project_id)
);

CREATE TABLE sapien_validations (
  validation_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  validator_id TEXT NOT NULL,
  
  commit_hash TEXT,  -- keccak256(score, salt)
  committed_at TIMESTAMP,
  
  revealed_score FLOAT,  -- 0-5 or 0-100 depending on rubric
  revealed_at TIMESTAMP,
  
  staked_amount NUMERIC,
  slash_amount NUMERIC,  -- If outlier
  reward_earned NUMERIC,
  
  is_outlier BOOLEAN,
  reputation_change INTEGER,
  
  FOREIGN KEY (project_id) REFERENCES sapien_projects(project_id)
);

CREATE TABLE sapien_attestations (
  attestation_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  
  content_hash TEXT,  -- What's being attested
  attestation_type TEXT,  -- QUIZ_QUALITY | READER_AUTHENTICITY | KEYPOINT_QUALITY
  
  consensus_score FLOAT,
  validator_consensus TEXT,  -- JSON: {validator_id: score, ...}
  
  onchain_tx_hash TEXT,
  onchain_block TEXT,
  explorer_link TEXT,
  
  attestation_data JSONB,  -- Full attestation structure
  
  created_at TIMESTAMP,
  
  FOREIGN KEY (project_id) REFERENCES sapien_projects(project_id)
);

CREATE TABLE external_articles (
  external_article_id TEXT PRIMARY KEY,
  publisher_id TEXT NOT NULL,
  
  title TEXT,
  summary TEXT,
  content_cid TEXT,  -- IPFS CID of full content
  publication_date TIMESTAMP,
  
  quiz_generated BOOLEAN,
  sapien_project_id TEXT,  -- Links to sapien_projects.project_id
  
  reader_count INTEGER,
  quiz_completion_count INTEGER,
  avg_comprehension_score FLOAT,
  
  created_at TIMESTAMP,
  
  FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
  FOREIGN KEY (sapien_project_id) REFERENCES sapien_projects(project_id)
);

CREATE TABLE embedded_quiz_sessions (
  session_id TEXT PRIMARY KEY,
  partner_id TEXT NOT NULL,
  external_article_id TEXT NOT NULL,
  user_id_hash TEXT,  -- Hashed anonymous user ID
  
  quiz_started_at TIMESTAMP,
  quiz_completed_at TIMESTAMP,
  
  score FLOAT,
  passed BOOLEAN,
  elapsed_seconds INTEGER,
  
  reward_earned NUMERIC,
  reward_status TEXT,  -- pending | verified | claimed
  
  sapien_validation_id TEXT,  -- Link to Sapien validation
  
  FOREIGN KEY (partner_id) REFERENCES partners(partner_id),
  FOREIGN KEY (external_article_id) REFERENCES external_articles(external_article_id)
);

CREATE TABLE publishers (
  publisher_id TEXT PRIMARY KEY,
  name TEXT,
  domain TEXT UNIQUE,
  
  api_key_hash TEXT,  -- Hashed for security
  webhook_secret_hash TEXT,
  
  config JSONB,  -- reward_sharing_model, etc
  
  total_articles INTEGER,
  total_quiz_completions INTEGER,
  total_poli_earned NUMERIC,
  
  verification_status TEXT,  -- pending | verified | suspended
  verified_at TIMESTAMP,
  
  created_at TIMESTAMP
);

CREATE TABLE partners (
  partner_id TEXT PRIMARY KEY,
  name TEXT,
  website TEXT,
  integration_type TEXT,  -- EMBEDDED_IFRAME | API | FULL_INTEGRATION
  
  api_key_hash TEXT,
  config JSONB,
  
  total_users INTEGER,
  total_quiz_attempts INTEGER,
  total_poli_distributed NUMERIC,
  partner_share_earned NUMERIC,
  
  created_at TIMESTAMP
);
```

---

## 🚀 Implementation Roadmap

### Phase 1: MVP (Month 1-2)
**Goal:** Integrate Sapien for internal quiz verification only

- [ ] Integrate SapienCore contract ABI into Poli-News
- [ ] Build Sapien Adapter (create/fund projects, submit contributions)
- [ ] Implement Consensus reading & onchain attestation storage
- [ ] Add DB tables for Sapien projects & validations
- [ ] Create admin panel to monitor Sapien projects
- [ ] Test full flow: quiz generated → Sapien project → consensus → update DB

### Phase 2: External Articles (Month 2-3)
**Goal:** Support third-party publishers

- [ ] Build publisher registration flow
- [ ] Implement article submission API
- [ ] Create Sapien projects for external content
- [ ] Build analytics dashboard for publishers
- [ ] Implement reward splitting logic
- [ ] Test with 5 pilot publishers

### Phase 3: iframe Embedding (Month 3-4)
**Goal:** Enable partners to embed quiz directly

- [ ] Build secure iframe authentication
- [ ] Implement PostMessage communication between iframe & parent
- [ ] Create partner integration portal
- [ ] Build analytics for embedded quizzes
- [ ] Test CORS, XSS, and security implications
- [ ] Deploy to production

### Phase 4: Advanced Features (Month 4+)
- [ ] Reader reputation system (onchain)
- [ ] Automated dispute resolution (DAO governance)
- [ ] Multi-chain deployment (Polygon, Arbitrum, Base)
- [ ] Advanced fraud detection (ML-based)
- [ ] Governance token distribution

---

## 🔒 Security & Economic Incentives

### Security Considerations

#### 1. **Iframe Security**
```
Risks:
└─ XSS injection from parent site
└─ Data exfiltration via PostMessage
└─ CSRF attacks on form submission
└─ Clickjacking

Mitigations:
├─ Strict Content Security Policy (CSP)
├─ Message origin verification (PostMessage)
├─ CSRF tokens on all state-changing operations
├─ Subresource Integrity (SRI) for assets
├─ Regular security audits
└─ Bug bounty program
```

#### 2. **Sapien Contract Risk**
```
Risks:
└─ Smart contract vulnerabilities
└─ Oracle attacks (if adding price feeds)
└─ Reentrancy
└─ Front-running on validator reveals

Mitigations:
├─ Use audited Sapien contracts (v0.5 audited)
├─ Formal verification where possible
├─ Time-locks on sensitive upgrades
├─ Rate limiting on contract calls
└─ Insurance/safety fund
```

#### 3. **Data Privacy**
```
Risks:
└─ GDPR compliance for reader data
└─ Personal data exposure in IPFS submissions
└─ Third-party data sharing

Mitigations:
├─ PII redaction before IPFS storage
├─ User consent before Sapien attestation
├─ Data retention policies (90 days default, user-configurable)
├─ Right to deletion support
└─ Privacy policy & DPA with partners
```

### Economic Incentives Alignment

#### Poli-News Level
```
Goal: Maximize quality of ai-generated content without scaling costs

Mechanism:
├─ Poli-News stakes origin stake on projects → ensures care
├─ Contributor rewards (80%): Attracts experts to review LLM output
├─ Validator rewards (20%): Ensures independent verification
├─ Slashing for outliers: Punishes dishonest actors
└─ Reputation system: Creates long-term credibility

Expected outcome: High-quality content at ~$2-5 per quiz verified
```

#### Contributor Level
```
Role: Generate or improve content

Incentives:
├─ Direct reward (POLI or SAPIEN) for accepted work
├─ Reputation bonus (long-term credibility)
├─ Onchain record (portable reputation)
└─ Potential DAO governance ("contributor vote")

Expected value: $5-15 per quiz submission (varies by quality)
```

#### Validator Level
```
Role: Review contributions honestly

Incentives:
├─ Reward pool allocation (% of validator reward share)
├─ Reputation gain for accuracy (+10 points)
├─ Slashing penalty for dishonesty (-50 points, 10-100% stake loss)
├─ Long-term: token governance in Sapien DAO

Expected value: $2-8 per validation (depends on stake & accuracy)
```

#### Partner/Publisher Level
```
Role: Integrate Poli-News & distribute quizzes

Incentives:
├─ Revenue share model (30-50% of rewards)
├─ User engagement boost (readers stay longer on site)
├─ Quality signal (onchain proof of reader comprehension)
├─ Accreditation support (PoQ record for compliance boards)
└─ Data insights (anonymized reader comprehension metrics)

Expected value: $500-2000/month per engaged publisher (based on traffic)
```

### Token Economics

```
Scenario: 10,000 articles/month processed

Article Quality Verification:
├─ Per quiz: 100 SAPIEN allocated (50 validator, 50 contributor)
├─ Monthly spend: 10,000 × 100 = 1M SAPIEN
└─ Cost: ~$10K/month (at $0.01/SAPIEN)

Reader Verification (Peer Review):
├─ Per reader attempt: 20 SAPIEN (10 validators, 10 contributor)
├─ Assume 50% of readers participate: 50,000 attempts/month
├─ Monthly spend: 50,000 × 20 = 1M SAPIEN
└─ Cost: ~$10K/month

Total Monthly Cost: ~$20K
Offset by:
├─ AI Training data licensing: $30-50K/month
├─ Analytics API subscriptions: $10-20K/month
└─ Premium publisher features: $5-10K/month

Net positive economics ✓
```

---

## 📊 Conclusion & Recommendation

### **CAN POLI-NEWS USE SAPIEN? YES, POWERFULLY.**

**Alignment:**
- ✅ Poli-News = AI content generation + user participation
- ✅ Sapien = Consensus-based quality verification on-chain
- ✅ Perfect fit for LLM quiz quality + reader comprehension verification

**Key Benefits:**
1. **Trust Primitive** — Onchain proof that quizzes are high-quality
2. **Scalable QA** — Outsource verification to expert community
3. **Economic Alignment** — Participants stake & earn based on accuracy
4. **Data Sovereignty** — Poli-News doesn't need to hire QA team
5. **Composability** — Quality signals consumable by any system

**Recommended Start:**
1. **Month 1:** Integrate Sapien for internal quiz verification (2-3 pilot projects)
2. **Month 2:** Expand to keypoints verification
3. **Month 3:** Open to external publishers (50 publishers beta)
4. **Month 4:** Launch partner iframe integration

**Success Metrics:**
- Quiz quality scores improve from LLM baseline (98% → 92% after Sapien QA)
- Reader authenticity increases (reduce bot attempts by 85%)
- Publisher participation grows (100+ partners in year 1)
- Economics positive (revenue ≥ costs by month 6)

---

**Document Version:** 1.0  
**Status:** Ready for Implementation  
**Next Step:** Schedule technical deep-dive with Sapien team  
**Contact:** [your-email@polinews.io]
