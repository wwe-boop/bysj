"""
实验批跑管理器
支持多场景、多参数的批量实验执行和统计分析
"""

import os
import json
import time
import logging
import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path

from ..simulation.simulation_engine import SimulationEngine
from ..scenarios.scenario_manager import ScenarioManager
from .statistical_analysis import StatisticalAnalyzer
from .experiment_config import ExperimentConfig, AblationConfig


@dataclass
class ExperimentResult:
    """单次实验结果"""
    experiment_id: str
    config: Dict[str, Any]
    metrics: Dict[str, float]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class BatchExperimentRunner:
    """批量实验运行器"""
    
    def __init__(self, output_dir: str = "experiments/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.scenario_manager = ScenarioManager()
        self.statistical_analyzer = StatisticalAnalyzer()
        
        # 实验结果存储
        self.results: List[ExperimentResult] = []
        self.current_batch_id = None
        
    def run_batch_experiments(self, 
                            experiment_configs: List[ExperimentConfig],
                            num_runs: int = 5,
                            parallel_workers: int = 4,
                            save_intermediate: bool = True) -> List[ExperimentResult]:
        """
        运行批量实验
        
        Args:
            experiment_configs: 实验配置列表
            num_runs: 每个配置的重复运行次数
            parallel_workers: 并行工作进程数
            save_intermediate: 是否保存中间结果
            
        Returns:
            实验结果列表
        """
        self.current_batch_id = f"batch_{int(time.time())}"
        self.logger.info(f"开始批量实验: {self.current_batch_id}")
        self.logger.info(f"实验配置数: {len(experiment_configs)}, 重复次数: {num_runs}")
        
        # 生成所有实验任务
        experiment_tasks = []
        for config_idx, config in enumerate(experiment_configs):
            for run_idx in range(num_runs):
                experiment_id = f"{self.current_batch_id}_config_{config_idx}_run_{run_idx}"
                experiment_tasks.append((experiment_id, config, run_idx))
        
        self.logger.info(f"总实验任务数: {len(experiment_tasks)}")
        
        # 并行执行实验
        results = []
        with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._run_single_experiment, task[0], task[1], task[2]): task
                for task in experiment_tasks
            }
            
            # 收集结果
            completed_count = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    self.logger.info(f"实验完成 ({completed_count}/{len(experiment_tasks)}): {task[0]}")
                    
                    # 保存中间结果
                    if save_intermediate and completed_count % 10 == 0:
                        self._save_intermediate_results(results)
                        
                except Exception as e:
                    self.logger.error(f"实验失败 {task[0]}: {e}")
                    # 创建失败结果记录
                    failed_result = ExperimentResult(
                        experiment_id=task[0],
                        config=asdict(task[1]),
                        metrics={},
                        execution_time=0.0,
                        success=False,
                        error_message=str(e)
                    )
                    results.append(failed_result)
        
        self.results.extend(results)
        
        # 保存最终结果
        self._save_batch_results(results)
        
        self.logger.info(f"批量实验完成: {len(results)} 个结果")
        return results
    
    def run_ablation_study(self, 
                          base_config: ExperimentConfig,
                          ablation_config: AblationConfig,
                          num_runs: int = 10) -> Dict[str, List[ExperimentResult]]:
        """
        运行消融实验
        
        Args:
            base_config: 基础配置
            ablation_config: 消融配置
            num_runs: 每个配置的重复次数
            
        Returns:
            按消融维度分组的实验结果
        """
        self.logger.info("开始消融实验")
        
        ablation_results = {}
        
        # 1. 状态空间消融
        if ablation_config.state_ablations:
            self.logger.info("执行状态空间消融")
            state_configs = self._generate_state_ablation_configs(base_config, ablation_config.state_ablations)
            state_results = self.run_batch_experiments(state_configs, num_runs)
            ablation_results['state_ablation'] = state_results
        
        # 2. 奖励函数消融
        if ablation_config.reward_ablations:
            self.logger.info("执行奖励函数消融")
            reward_configs = self._generate_reward_ablation_configs(base_config, ablation_config.reward_ablations)
            reward_results = self.run_batch_experiments(reward_configs, num_runs)
            ablation_results['reward_ablation'] = reward_results
        
        # 3. 动作空间消融
        if ablation_config.action_ablations:
            self.logger.info("执行动作空间消融")
            action_configs = self._generate_action_ablation_configs(base_config, ablation_config.action_ablations)
            action_results = self.run_batch_experiments(action_configs, num_runs)
            ablation_results['action_ablation'] = action_results
        
        # 4. 算法比较
        if ablation_config.algorithm_comparisons:
            self.logger.info("执行算法比较")
            algo_configs = self._generate_algorithm_comparison_configs(base_config, ablation_config.algorithm_comparisons)
            algo_results = self.run_batch_experiments(algo_configs, num_runs)
            ablation_results['algorithm_comparison'] = algo_results
        
        # 保存消融结果
        self._save_ablation_results(ablation_results)
        
        return ablation_results
    
    def _run_single_experiment(self, experiment_id: str, config: ExperimentConfig, run_idx: int) -> ExperimentResult:
        """运行单个实验"""
        start_time = time.time()
        
        try:
            # 创建仿真引擎
            engine = SimulationEngine()
            
            # 加载场景
            scenario = self.scenario_manager.get_scenario(config.scenario_name)
            if not scenario:
                raise ValueError(f"场景不存在: {config.scenario_name}")
            
            # 应用实验配置
            self._apply_experiment_config(engine, config)
            
            # 运行仿真
            engine.load_scenario(scenario)
            engine.run_simulation(config.duration_seconds)
            
            # 收集指标
            metrics = self._collect_experiment_metrics(engine)
            
            execution_time = time.time() - start_time
            
            return ExperimentResult(
                experiment_id=experiment_id,
                config=asdict(config),
                metrics=metrics,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ExperimentResult(
                experiment_id=experiment_id,
                config=asdict(config),
                metrics={},
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    def _apply_experiment_config(self, engine: SimulationEngine, config: ExperimentConfig):
        """应用实验配置到仿真引擎"""
        # 配置准入控制
        if config.admission_config:
            admission_controller = engine.admission_controller
            for key, value in config.admission_config.items():
                if hasattr(admission_controller, key):
                    setattr(admission_controller, key, value)
        
        # 配置DSROQ
        if config.dsroq_config:
            dsroq_controller = engine.dsroq_controller
            for key, value in config.dsroq_config.items():
                if hasattr(dsroq_controller, key):
                    setattr(dsroq_controller, key, value)
        
        # 配置定位服务
        if config.positioning_config:
            positioning_service = engine.positioning_service
            for key, value in config.positioning_config.items():
                if hasattr(positioning_service, key):
                    setattr(positioning_service, key, value)
        
        # 配置网络参数
        if config.network_config:
            network_state = engine.network_state
            for key, value in config.network_config.items():
                if hasattr(network_state, key):
                    setattr(network_state, key, value)
    
    def _collect_experiment_metrics(self, engine: SimulationEngine) -> Dict[str, float]:
        """收集实验指标"""
        performance_monitor = engine.performance_monitor
        
        # 获取最终性能指标
        final_metrics = performance_monitor.get_current_metrics()
        
        # 计算平均指标
        history = performance_monitor.get_performance_history()
        if history:
            avg_metrics = {
                'avg_qoe': np.mean([m.qoe_score for m in history]),
                'avg_throughput': np.mean([m.average_throughput for m in history]),
                'avg_latency': np.mean([m.average_latency for m in history]),
                'avg_admission_rate': np.mean([m.admission_rate for m in history]),
                'avg_positioning_accuracy': np.mean([m.positioning_accuracy for m in history]),
                'avg_gdop': np.mean([m.gdop for m in history]),
                'total_requests': sum([m.total_requests for m in history]),
                'total_accepted': sum([m.accepted_requests for m in history]),
                'total_rejected': sum([m.rejected_requests for m in history])
            }
        else:
            avg_metrics = {}
        
        # 合并指标
        metrics = {
            'final_qoe': final_metrics.qoe_score,
            'final_throughput': final_metrics.average_throughput,
            'final_latency': final_metrics.average_latency,
            'final_admission_rate': final_metrics.admission_rate,
            'final_positioning_accuracy': final_metrics.positioning_accuracy,
            'final_gdop': final_metrics.gdop,
            **avg_metrics
        }
        
        return metrics
    
    def _generate_state_ablation_configs(self, base_config: ExperimentConfig, ablations: List[str]) -> List[ExperimentConfig]:
        """生成状态空间消融配置"""
        configs = []
        
        for ablation in ablations:
            config = ExperimentConfig(**asdict(base_config))
            config.experiment_name = f"{base_config.experiment_name}_state_ablation_{ablation}"
            
            # 根据消融类型修改配置
            if ablation == "no_positioning":
                config.admission_config = config.admission_config or {}
                config.admission_config['use_positioning'] = False
            elif ablation == "no_load_info":
                config.admission_config = config.admission_config or {}
                config.admission_config['use_load_info'] = False
            elif ablation == "no_history":
                config.admission_config = config.admission_config or {}
                config.admission_config['use_history'] = False
            
            configs.append(config)
        
        return configs
    
    def _generate_reward_ablation_configs(self, base_config: ExperimentConfig, ablations: List[str]) -> List[ExperimentConfig]:
        """生成奖励函数消融配置"""
        configs = []
        
        for ablation in ablations:
            config = ExperimentConfig(**asdict(base_config))
            config.experiment_name = f"{base_config.experiment_name}_reward_ablation_{ablation}"
            
            # 修改奖励权重
            if ablation == "no_fairness":
                config.admission_config = config.admission_config or {}
                config.admission_config['reward_weights'] = {
                    'qoe_weight': 0.5,
                    'fairness_weight': 0.0,
                    'efficiency_weight': 0.3,
                    'stability_weight': 0.2
                }
            elif ablation == "no_efficiency":
                config.admission_config = config.admission_config or {}
                config.admission_config['reward_weights'] = {
                    'qoe_weight': 0.5,
                    'fairness_weight': 0.3,
                    'efficiency_weight': 0.0,
                    'stability_weight': 0.2
                }
            
            configs.append(config)
        
        return configs
    
    def _generate_action_ablation_configs(self, base_config: ExperimentConfig, ablations: List[str]) -> List[ExperimentConfig]:
        """生成动作空间消融配置"""
        configs = []
        
        for ablation in ablations:
            config = ExperimentConfig(**asdict(base_config))
            config.experiment_name = f"{base_config.experiment_name}_action_ablation_{ablation}"
            
            # 修改动作空间
            if ablation == "binary_only":
                config.admission_config = config.admission_config or {}
                config.admission_config['action_space'] = ['accept', 'reject']
            elif ablation == "no_degraded":
                config.admission_config = config.admission_config or {}
                config.admission_config['action_space'] = ['accept', 'reject', 'delay']
            
            configs.append(config)
        
        return configs
    
    def _generate_algorithm_comparison_configs(self, base_config: ExperimentConfig, algorithms: List[str]) -> List[ExperimentConfig]:
        """生成算法比较配置"""
        configs = []
        
        for algorithm in algorithms:
            config = ExperimentConfig(**asdict(base_config))
            config.experiment_name = f"{base_config.experiment_name}_algo_{algorithm}"
            config.admission_config = config.admission_config or {}
            config.admission_config['algorithm'] = algorithm
            
            configs.append(config)
        
        return configs
    
    def _save_intermediate_results(self, results: List[ExperimentResult]):
        """保存中间结果"""
        filename = self.output_dir / f"{self.current_batch_id}_intermediate.json"
        with open(filename, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
    
    def _save_batch_results(self, results: List[ExperimentResult]):
        """保存批量实验结果"""
        # 保存JSON格式
        json_filename = self.output_dir / f"{self.current_batch_id}_results.json"
        with open(json_filename, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        # 保存CSV格式
        csv_filename = self.output_dir / f"{self.current_batch_id}_results.csv"
        df = self._results_to_dataframe(results)
        df.to_csv(csv_filename, index=False)
        
        self.logger.info(f"批量结果已保存: {json_filename}, {csv_filename}")
    
    def _save_ablation_results(self, ablation_results: Dict[str, List[ExperimentResult]]):
        """保存消融实验结果"""
        for ablation_type, results in ablation_results.items():
            filename = self.output_dir / f"{self.current_batch_id}_{ablation_type}.json"
            with open(filename, 'w') as f:
                json.dump([asdict(r) for r in results], f, indent=2)
    
    def _results_to_dataframe(self, results: List[ExperimentResult]) -> pd.DataFrame:
        """将结果转换为DataFrame"""
        data = []
        for result in results:
            row = {
                'experiment_id': result.experiment_id,
                'success': result.success,
                'execution_time': result.execution_time,
                'timestamp': result.timestamp
            }
            
            # 添加配置信息
            for key, value in result.config.items():
                row[f'config_{key}'] = value
            
            # 添加指标信息
            for key, value in result.metrics.items():
                row[f'metric_{key}'] = value
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def generate_statistical_report(self, results: List[ExperimentResult]) -> Dict[str, Any]:
        """生成统计分析报告"""
        return self.statistical_analyzer.analyze_experiment_results(results)
