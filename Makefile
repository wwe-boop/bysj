.PHONY: setup run-api plots build-pdf hypatia-init

setup:
	python -m pip install -U pip
	pip install -r requirements.txt
	@echo "Setup done. For conda: conda env create -f environment.yml"

run-api:
	python src/api/main.py

plots:
	python scripts/plots/qoe_metrics_plot.py \
		--input experiments/results/positioning_ablation_example.json \
		--output docs/assets/ablation_qoe_positioning.png
	python scripts/plots/admission_rates_plot.py \
		--input experiments/results/positioning_ablation_example.json \
		--output docs/assets/ablation_rates_positioning.png
	python scripts/plots/fairness_heatmap.py \
		--input experiments/results/sensitivity_matrix.json \
		--output docs/assets/ablation_sensitivity_positioning.png

build-pdf:
	bash docs/latex/build.sh

hypatia-init:
	bash scripts/setup/hypatia_init.sh
