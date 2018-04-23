#!/bin/bash
#SBATCH --job-name=serial-job
#SBATCH --time=48:0:0
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=shared
#SBATCH --mem=3000

set -eo pipefail

. /work-zfs/lhc/cms/cmsset_default.sh
set -u
cd $CMSSW_BASE
eval $(scram ru -sh)
if ! [ -z ${SLURM_SUBMIT_DIR+x} ]; then cd ${SLURM_SUBMIT_DIR}; else cd -; fi
cd ..
echo "SLURM job running in: " `pwd`

./JHUGen Unweighted=0 VegasNc0=99999999 VegasNc1=99999999 VegasNc2=99999999 PDFSet=3 Interf=0 "$@"
