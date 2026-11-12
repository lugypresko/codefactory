#!/bin/bash
# Mirrors lib/pipeline.py per-issue steps for ONE issue in a scratch worktree (non-scored). usage: smoke_driver.sh <root> <iid> <mode: inject|real>
set -u; cd "$1"; I=$2; MODE=$3; PY=.venv/bin/python; L=work/smoke.log; ts(){ date '+%F %T'; }
log(){ echo "[$(ts)] $*" | tee -a $L; }
log "SMOKE ($MODE) $I start; HEAD $(git rev-parse --short HEAD)"
if [ "$MODE" = real ]; then
  log "stage1 testgen"; $PY lib/stage1_testgen.py $I 2>&1 | grep -v "mini-swe\|migration\|Loading global" | tee -a $L; rc=${PIPESTATUS[0]}; log "stage1 rc=$rc"; [ $rc = 3 ] && { log "INFRA_FAIL halt"; exit 3; }
  $PY lib/stage1b_pre.py $I 2>&1 | tee -a $L
  git add results/testgen/$I && git commit -qm "SMOKE STAGE1 FREEZE $I" && log "stage1 frozen $(git rev-parse --short HEAD) (patch dir exists: $(test -e results/patches/$I && echo yes || echo no))"
fi
RID="pa-$I-$(date +%Y%m%dT%H%M%S)-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' \n')"
log "stage2 run_id=$RID"; $PY lib/stage2_patch.py $I $RID 2>&1 | tee -a $L; rc=${PIPESTATUS[0]}; [ $rc = 4 ] && { log "INTEGRITY_FAIL stage2"; exit 4; }
git add results/patches/$I && git commit -qm "STAGE2 SEAL $I run $RID" && log "stage2 sealed $(git rev-parse --short HEAD)"
log "stage3"; $PY lib/stage3_eval.py $I $RID 2>&1 | tee -a $L; rc=${PIPESTATUS[0]}; log "stage3 rc=$rc"
log "SMOKE ($MODE) end"
