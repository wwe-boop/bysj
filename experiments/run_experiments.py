"""
实验批处理运行脚本

该脚本用于自动化执行一系列实验场景，并生成结果。
主要功能包括：
1. 从YAML文件加载实验场景配置。
2. 循环执行每个场景，运行仿真。
3. 将每个场景的仿真结果保存为结构化的JSON文件。
4. （可选）在所有仿真结束后，自动调用绘图脚本生成图表。
"""

import os
import argparse
import yaml
import json
from datetime import datetime
from pathlib import Path

# 假设的导入路径，需要根据实际项目结构调整
from src.core.config import load_config, SystemConfig
from src.simulation.simulation_engine import SimulationEngine

# 假设结果和绘图脚本的路径
RESULTS_DIR = Path(__file__).parent / "results"
PLOTS_DIR = Path(__file__).parent.parent / "docs" / "assets"
PLOT_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts" / "plots"


def run_single_experiment(exp_name: str, base_config: SystemConfig, scenario_config: dict) -> Path:
    """
    运行单个实验场景。
    """
    print(f"--- Running experiment: {exp_name} ---")

    # 1. 更新配置 (这里需要一个辅助函数来深度合并配置)
    # 简化处理：直接修改 base_config 对象
    # TODO: 实现更健壮的配置覆盖逻辑
    if 'simulation' in scenario_config:
        for key, value in scenario_config['simulation'].items():
            if hasattr(base_config.simulation, key):
                setattr(base_config.simulation, key, value)
    
    # 2. 初始化并运行仿真引擎
    try:
        engine = SimulationEngine(base_config)
        result = engine.run_simulation()

        # 3. 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"{exp_name}_{timestamp}.json"
        result_path = RESULTS_DIR / result_filename
        
        RESULTS_DIR.mkdir(exist_ok=True)
        with open(result_path, 'w', encoding='utf-8') as f:
            # 将dataclass转换为可序列化的字典
            # TODO: 完善SimulationResult的序列化
            json.dump(result.detailed_metrics, f, indent=2)

        print(f"--- Experiment {exp_name} finished. Results saved to {result_path} ---")
        return result_path

    except Exception as e:
        print(f"!!! Experiment {exp_name} failed: {e} !!!")
        return None


def main():
    parser = argparse.ArgumentParser(description="Run batch experiments for the LEO satellite network simulation.")
    parser.add_argument(
        "--config",
        type=str,
        default="experiments/configs/default.yaml",
        help="Path to the base configuration file."
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default="experiments/scenarios/defaults.yaml",
        help="Path to the scenarios definition file."
    )
    parser.add_argument(
        "--exp",
        type=str,
        default=None,
        help="Run a single experiment by name instead of all."
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Do not generate plots after running experiments."
    )
    args = parser.parse_args()

    # 加载基础配置和场景
    base_config = load_config(args.config)
    with open(args.scenarios, 'r', encoding='utf-8') as f:
        scenarios = yaml.safe_load(f)

    # 运行实验
    results_paths = []
    if args.exp:
        if args.exp in scenarios:
            result_path = run_single_experiment(args.exp, base_config, scenarios[args.exp])
            if result_path:
                results_paths.append(result_path)
        else:
            print(f"Error: Experiment '{args.exp}' not found in {args.scenarios}")
            return
    else:
        for name, config in scenarios.items():
            result_path = run_single_experiment(name, base_config, config)
            if result_path:
                results_paths.append(result_path)

    print("\n--- All experiments finished. ---")

    # 生成图表
    if not args.no_plots and results_paths:
        print("\n--- Generating plots... ---")
        # TODO: 这里需要一个更智能的方式来聚合多个实验结果用于绘图
        # 简化：只为最后一个结果生成图表
        last_result = results_paths[-1]
        
        plot_scripts = [
            "qoe_metrics_plot.py",
            "admission_rates_plot.py",
            "fairness_heatmap.py" # 这个需要不同的输入格式
        ]

        PLOTS_DIR.mkdir(exist_ok=True)

        for script in plot_scripts:
            script_path = PLOT_SCRIPTS_DIR / script
            if script_path.exists():
                output_file = PLOTS_DIR / f"{last_result.stem}_{script.replace('.py', '.png')}"
                command = f"python {script_path} --input {last_result} --output {output_file}"
                print(f"Running: {command}")
                try:
                    os.system(command)
                except Exception as e:
                    print(f"Failed to run plot script {script}: {e}")
            else:
                print(f"Warning: Plot script not found: {script_path}")
    
    print("\n--- Batch run complete. ---")


if __name__ == "__main__":
    main()
