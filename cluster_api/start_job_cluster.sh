#!/bin/bash

# This script should lay on the cluster side in the home dir.
# This assumes the cluster uses slurm as a work manager.

sbatch <<EOT
#!/bin/bash

#SBATCH --job-name=$1
#SBATCH --chdir=$2/$1
#SBATCH --output=$2/$1/slurm.log
#SBATCH --time=0-00:30:00
#SBATCH --mem-per-cpu=1G

module load foss/2022b Python/3.10.8

source $3/bin/activate

python3 $4/SM_prediction_main.py -wd $2/$1

exit 0
EOT
