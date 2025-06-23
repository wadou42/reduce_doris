import os
import typing
from typing import Optional, Union
import random

from z3 import *

def get_opt_negation(option: str) -> str:
    if "-fno-" in option.strip():
        return option.strip().replace("-fno-", "-f", 1)
    else:
        return option.strip().replace("-f", "-fno-", 1)
    


class ConstrainsSolver:
    def __init__(self, constrains_file: str):
        self.option_constrains: list[list[str]] = []
        if os.path.exists(constrains_file):
            f = open(constrains_file)
            constrains_file_lines = f.readlines()
            print(f"Constrains file: {constrains_file}, lines: {len(constrains_file_lines)}")
            f.close()
            for line in constrains_file_lines:
                line = line.strip()
                if line.startswith('-'):
                    self.option_constrains.append(line.split(' '))
    
    def add_constrain(self, constrain: list[str]):
        self.option_constrains.append(constrain)

    def solve(self,opt_config: dict[str, str]):
        
        # pre_process
        all_single_constrain = set()
        for constrain_list in self.option_constrains:
            if len(constrain_list) > 1:
                continue
            constrain = constrain_list[0]
            all_single_constrain.add(constrain)
            if get_opt_negation(constrain) in all_single_constrain:
                opt_config.pop(constrain, None)
                opt_config.pop(get_opt_negation(constrain), None)
        
        all_cond: list[BoolRef] = []
        constrained_option_bool_refs: dict[str, BoolRef] = dict()
        
        for opt_constrain in self.option_constrains:
            single_cond: list[BoolRef] = []

            # we should ensure that all options are in config.
            options_in_config = [1 for option in opt_constrain
                                 if option in opt_config or get_opt_negation(option) in opt_config]
            if len(options_in_config) != len(opt_constrain):
                continue

            for option in opt_constrain:
                if option not in constrained_option_bool_refs:  # z3 boolref not created
                    if option not in opt_config:  # close in constrains
                        assert get_opt_negation(option) in opt_config
                        option = get_opt_negation(option)
                        z3_bv = Bool(option)
                        single_cond.append(Not(z3_bv))
                    else:  # open in constrains
                        z3_bv = Bool(option)
                        single_cond.append(z3_bv)
                    constrained_option_bool_refs.setdefault(option, z3_bv)
                else:
                    if option not in opt_config:
                        option = get_opt_negation(option)
                        single_cond.append(Not(constrained_option_bool_refs[option]))
                    else:
                        single_cond.append(constrained_option_bool_refs[option])
            all_cond.append(And(single_cond))

        while True:
            random_cond: list[BoolRef] = []
            for opt_constrain in self.option_constrains:

                # we should ensure that all options are in config.
                options_in_config = [1 for option in opt_constrain
                                     if option in opt_config or get_opt_negation(option) in opt_config]
                if len(options_in_config) != len(opt_constrain):
                    continue

                for option in opt_constrain:
                    if option not in opt_config:
                        option = get_opt_negation(option)
                    if len(opt_constrain) > 1 and random.randint(0, 1) == 1:
                        if random.randint(0, 1) == 1:
                            random_cond.append(constrained_option_bool_refs[option])
                        else:
                            random_cond.append(Not(constrained_option_bool_refs[option]))
            random_cond = And(random_cond)
            solver = Solver()
            solver.add(And(Not(Or(all_cond)), random_cond))
            if solver.check() == sat:
                break

        model = solver.model()
        for option in constrained_option_bool_refs:
            opt_config[option] =  bool(model[constrained_option_bool_refs[option]])
            # print(f'{option}={model[constrained_option_bool_refs[option]]}')
        return opt_config


if __name__ == '__main__':

    print('*'*50)
    optconfig = "-faggressive-loop-optimizations -fallocation-dce -fasynchronous-unwind-tables -fno-auto-inc-dec -fbit-tests -fdce -fearly-inlining -fno-fp-int-builtin-inexact -fno-function-cse -fno-gcse-lm -finline-atomics -fno-ipa-stack-alignment -fipa-strict-aliasing -fno-ira-hoist-pressure -fira-share-save-slots -fno-ira-share-spill-slots -fivopts -fno-jump-tables -fno-lifetime-dse -fno-math-errno -fomit-frame-pointer -fno-peephole -fplt -fno-printf-return-value -freg-struct-return -fno-sched-critical-path-heuristic -fsched-dep-count-heuristic -fsched-group-heuristic -fsched-interblock -fsched-last-insn-heuristic -fsched-rank-heuristic -fno-sched-spec -fno-sched-spec-insn-heuristic -fno-sched-stalled-insns-dep -fno-schedule-fusion -fno-semantic-interposition -fshort-enums -fshrink-wrap-separate -fno-signed-zeros -fsplit-ivs-in-unroller -fno-ssa-backprop -fno-stdarg-opt -fstrict-volatile-bitfields -fno-trapping-math -ftree-forwprop -ftree-loop-im -fno-tree-loop-ivcanon -fno-tree-loop-optimize -fno-tree-phiprop -fno-tree-reassoc -fno-tree-scev-cprop -fno-unwind-tables -fno-branch-count-reg -fcombine-stack-adjustments -fno-compare-elim -fno-cprop-registers -fdefer-pop -fno-dse -fforward-propagate -fguess-branch-probability -fno-if-conversion -fno-if-conversion2 -finline -finline-functions-called-once -fipa-modref -fipa-profile -fipa-pure-const -fipa-reference -fno-ipa-reference-addressable -fno-move-loop-invariants -fmove-loop-stores -fno-reorder-blocks -fno-sched-pressure -fsection-anchors -fno-shrink-wrap -fno-split-wide-types -fno-ssa-phiopt -fthread-jumps -ftoplevel-reorder -ftree-bit-ccp -fno-tree-builtin-call-dce -fno-tree-ccp -ftree-ch -ftree-coalesce-vars -fno-tree-copy-prop -ftree-dce -fno-tree-dominator-opts -fno-tree-dse -ftree-fre -fno-tree-pta -ftree-sink -fno-tree-slsr -fno-tree-sra -ftree-ter -falign-functions -fno-align-jumps -falign-labels -falign-loops -fno-caller-saves -fcode-hoisting -fcrossjumping -fcse-follow-jumps -fdevirtualize -fno-devirtualize-speculatively -fno-expensive-optimizations -fgcse -fno-hoist-adjacent-loads -fno-indirect-inlining -fno-inline-functions -finline-small-functions -fno-ipa-bit-cp -fipa-cp -fipa-icf -fno-ipa-icf-functions -fno-ipa-icf-variables -fipa-ra -fipa-sra -fipa-vrp -fisolate-erroneous-paths-dereference -flra-remat -foptimize-sibling-calls -fno-optimize-strlen -fpartial-inlining -fno-peephole2 -fno-ree -freorder-functions -fno-rerun-cse-after-loop -fschedule-insns -fno-schedule-insns2 -fstore-merging -fstrict-aliasing -fno-tree-loop-distribute-patterns -ftree-loop-vectorize -ftree-pre -fno-tree-slp-vectorize -ftree-switch-conversion -fno-tree-tail-merge -ftree-vrp -fno-gcse-after-reload -fno-ipa-cp-clone -fno-loop-interchange -fno-loop-unroll-and-jam -fno-peel-loops -fno-predictive-commoning -fno-split-loops -fsplit-paths -fno-tree-loop-distribution -fno-tree-partial-pre -fno-unroll-completely-grow-size -fno-unswitch-loops -fno-version-loops-for-strides -fallow-store-data-races -fno-array-widen-compare -fassociative-math -fbranch-probabilities -fccmp2 -fno-conserve-stack -fno-convert-minmax -fno-crypto-accel-aes -fcx-fortran-rules -fcx-limited-range -fno-delayed-branch -fno-delete-dead-exceptions -fexceptions -ffinite-loops -fno-finite-math-only -ffloat-store -fno-ftz -fno-gcse-las -fno-gcse-sm -fgraphite -fno-graphite-identity -fharden-compares -fharden-conditional-branches -ficp -ficp-speculatively -fno-if-conversion-gimple -fifcvt-allow-complicated-cmps -fno-ipa-ic -fipa-prefetch -fipa-pta -fipa-reorder-fields -fipa-struct-reorg -fira-loop-pressure -fisolate-erroneous-paths-attribute -fno-keep-gc-roots-live -fno-kernel-pgo -fno-limit-function-alignment -flive-range-shrinkage -fno-loop-crc -fno-loop-elim -floop-nest-optimize -floop-parallelize-all -fmerge-mull -fmodulo-sched -fmodulo-sched-allow-regmoves -fno-non-call-exceptions -fno-opt-info -fpack-struct -fprofile-partial-training -fno-profile-reorder-functions -freciprocal-math -fno-rename-registers -freorder-blocks-and-partition -freschedule-modulo-scheduled-loops -frounding-math -fsched-spec-load -fno-sched-spec-load-dangerous -fsched-stalled-insns -fno-sched2-use-superblocks -fno-sel-sched-pipelining -fno-sel-sched-pipelining-outer-loops -fsel-sched-reschedule-pipelined -fno-selective-scheduling -fno-selective-scheduling2 -fno-short-wchar -fsignaling-nans -fno-simdmath -fsingle-precision-constant -fno-split-ldp-stp -fsplit-wide-types-early -fno-stack-clash-protection -fstack-protector -fstack-protector-explicit -fstack-protector-strong -ftracer -fno-trapv -ftree-cselim -fno-tree-lrs -fno-tree-slp-transpose-vectorize -ftree-vectorize -fno-unconstrained-commons -funroll-all-loops -fno-unroll-loops -funsafe-math-optimizations -fvar-tracking -fno-var-tracking-assignments -fvar-tracking-assignments-toggle -fno-var-tracking-uninit -fvariable-expansion-in-unroller -fvpt -fno-web -fwrapv -fwrapv-pointer -gstatement-frontiers -mcmlt-arith -mlow-precision-div -mlow-precision-recip-sqrt -mlow-precision-sqrt -msimdmath-64 -fnothrow-opt -fno-prefetch-loop-arrays -fno-tree-loop-if-convert -fno-strict-enums -fdelete-null-pointer-checks -fno-fast-math -ffold-simple-inlines -frtti -fno-pack-struct"
    opt_dict = dict()
    for opt in optconfig.split():
        if "-fno-" in opt:
            opt_dict[opt.replace("-fno-", "-f", 1)] = False
        else:
            opt_dict[opt] = True
    print(len(opt_dict))
    seed = random.randint(1, 1000)
    print(f"Random seed: {seed}")
    set_param("smt.random_seed", seed)
    set_param("sat.random_seed", seed)
    c = ConstrainsSolver(constrains_file="constrains/rocksdb.txt")
    c.solve(opt_config=opt_dict)
    opt_str = " ".join(
        sorted(
            [opt if opt_dict[opt] else get_opt_negation(opt) 
            for opt in opt_dict.keys()]
        )
    )
    print(opt_str)