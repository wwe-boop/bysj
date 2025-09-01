"""
实验管理API路由
支持批量实验、消融实验、统计分析等功能
"""

import logging
import time
import json
import os
import asyncio
from flask import Blueprint, request, jsonify, send_file, current_app
from marshmallow import Schema, fields, ValidationError
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

experiments_bp = Blueprint('experiments', __name__)
logger = logging.getLogger(__name__)

# 全局变量存储实验状态
_experiment_runner = None
_running_experiments = {}
_experiment_results = {}


class ExperimentConfigSchema(Schema):
    """实验配置验证模式"""
    experiment_name = fields.Str(required=True)
    scenario_name = fields.Str(required=True)
    duration_seconds = fields.Int(missing=300)
    num_runs = fields.Int(missing=5)
    parallel_workers = fields.Int(missing=2)
    
    # 配置参数
    admission_config = fields.Dict(missing=dict)
    dsroq_config = fields.Dict(missing=dict)
    positioning_config = fields.Dict(missing=dict)
    network_config = fields.Dict(missing=dict)
    
    # 实验参数
    random_seed = fields.Int(allow_none=True)
    description = fields.Str(missing="")
    tags = fields.List(fields.Str(), missing=list)


class AblationConfigSchema(Schema):
    """消融实验配置验证模式"""
    state_ablations = fields.List(fields.Str(), missing=list)
    reward_ablations = fields.List(fields.Str(), missing=list)
    action_ablations = fields.List(fields.Str(), missing=list)
    algorithm_comparisons = fields.List(fields.Str(), missing=list)
    load_ablations = fields.List(fields.Float(), missing=list)
    constellation_ablations = fields.List(fields.Str(), missing=list)
    failure_ablations = fields.List(fields.Str(), missing=list)


class BatchExperimentSchema(Schema):
    """批量实验配置验证模式"""
    experiment_configs = fields.List(fields.Nested(ExperimentConfigSchema), required=True)
    num_runs = fields.Int(missing=5)
    parallel_workers = fields.Int(missing=2)
    save_intermediate = fields.Bool(missing=True)


@experiments_bp.route('/batch/start', methods=['POST'])
def start_batch_experiments():
    """启动批量实验"""
    try:
        # 验证请求数据
        schema = BatchExperimentSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '批量实验配置无效',
                'details': err.messages
            }), 400
        
        # 检查是否有实验正在运行
        if _running_experiments:
            return jsonify({
                'success': False,
                'error': '已有实验正在运行，请等待完成后再启动新实验'
            }), 409
        
        # 创建实验ID
        experiment_id = f"batch_{int(time.time())}"
        
        # 启动后台实验任务
        def run_batch_experiment():
            try:
                from ....experiments.batch_runner import BatchExperimentRunner
                from ....experiments.experiment_config import ExperimentConfig
                
                # 创建实验运行器
                runner = BatchExperimentRunner()
                
                # 转换配置
                experiment_configs = []
                for config_data in data['experiment_configs']:
                    config = ExperimentConfig(**config_data)
                    experiment_configs.append(config)
                
                # 更新运行状态
                _running_experiments[experiment_id] = {
                    'status': 'running',
                    'progress': 0,
                    'total_experiments': len(experiment_configs) * data['num_runs'],
                    'completed_experiments': 0,
                    'start_time': time.time()
                }
                
                # 运行批量实验
                results = runner.run_batch_experiments(
                    experiment_configs,
                    num_runs=data['num_runs'],
                    parallel_workers=data['parallel_workers'],
                    save_intermediate=data['save_intermediate']
                )
                
                # 保存结果
                _experiment_results[experiment_id] = results
                _running_experiments[experiment_id]['status'] = 'completed'
                _running_experiments[experiment_id]['progress'] = 100
                
                # 通知前端完成
                try:
                    socketio = current_app.extensions.get('socketio')
                    if socketio:
                        socketio.emit('batch_experiment_completed', {
                            'experiment_id': experiment_id
                        }, broadcast=True)
                except Exception as _:
                    pass
                
                logger.info(f"批量实验完成: {experiment_id}")
                
            except Exception as e:
                logger.error(f"批量实验失败: {e}")
                _running_experiments[experiment_id]['status'] = 'failed'
                _running_experiments[experiment_id]['error'] = str(e)
        
        # 在后台线程中运行实验
        thread = threading.Thread(target=run_batch_experiment)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'experiment_id': experiment_id,
                'message': '批量实验已启动'
            }
        })
        
    except Exception as e:
        logger.error(f"启动批量实验失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/ablation/start', methods=['POST'])
def start_ablation_study():
    """启动消融实验"""
    try:
        data = request.get_json() or {}
        
        # 验证基础配置
        base_config_data = data.get('base_config', {})
        if not base_config_data:
            return jsonify({
                'success': False,
                'error': '缺少基础配置'
            }), 400
        
        # 验证消融配置
        ablation_schema = AblationConfigSchema()
        try:
            ablation_config = ablation_schema.load(data.get('ablation_config', {}))
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '消融配置无效',
                'details': err.messages
            }), 400
        
        # 创建实验ID
        experiment_id = f"ablation_{int(time.time())}"
        
        # 启动后台消融实验
        def run_ablation_study():
            try:
                from ....experiments.batch_runner import BatchExperimentRunner
                from ....experiments.experiment_config import ExperimentConfig, AblationConfig
                
                # 创建实验运行器
                runner = BatchExperimentRunner()
                
                # 创建基础配置
                base_config = ExperimentConfig(**base_config_data)
                ablation_cfg = AblationConfig(**ablation_config)
                
                # 更新运行状态
                _running_experiments[experiment_id] = {
                    'status': 'running',
                    'progress': 0,
                    'start_time': time.time()
                }
                
                # 运行消融实验
                results = runner.run_ablation_study(
                    base_config,
                    ablation_cfg,
                    num_runs=data.get('num_runs', 10)
                )
                
                # 保存结果
                _experiment_results[experiment_id] = results
                _running_experiments[experiment_id]['status'] = 'completed'
                _running_experiments[experiment_id]['progress'] = 100
                
                # 实时推送完成事件
                try:
                    socketio = current_app.extensions.get('socketio')
                    if socketio:
                        socketio.emit('ablation_completed', {
                            'experiment_id': experiment_id
                        }, broadcast=True)
                except Exception as _:
                    pass
                
                logger.info(f"消融实验完成: {experiment_id}")
                
            except Exception as e:
                logger.error(f"消融实验失败: {e}")
                _running_experiments[experiment_id]['status'] = 'failed'
                _running_experiments[experiment_id]['error'] = str(e)
        
        # 在后台线程中运行实验
        thread = threading.Thread(target=run_ablation_study)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'experiment_id': experiment_id,
                'message': '消融实验已启动'
            }
        })
        
    except Exception as e:
        logger.error(f"启动消融实验失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/status/<experiment_id>', methods=['GET'])
def get_experiment_status(experiment_id):
    """获取实验状态"""
    try:
        if experiment_id not in _running_experiments:
            return jsonify({
                'success': False,
                'error': '实验不存在'
            }), 404
        
        status = _running_experiments[experiment_id].copy()
        
        # 计算运行时间
        if 'start_time' in status:
            status['running_time'] = time.time() - status['start_time']
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取实验状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/results/<experiment_id>', methods=['GET'])
def get_experiment_results(experiment_id):
    """获取实验结果"""
    try:
        if experiment_id not in _experiment_results:
            return jsonify({
                'success': False,
                'error': '实验结果不存在'
            }), 404
        
        results = _experiment_results[experiment_id]
        
        # 转换结果为可序列化格式
        serializable_results = []
        for result in results:
            if hasattr(result, '__dict__'):
                serializable_results.append(result.__dict__)
            else:
                serializable_results.append(result)
        
        return jsonify({
            'success': True,
            'data': {
                'experiment_id': experiment_id,
                'results': serializable_results,
                'total_results': len(serializable_results)
            }
        })
        
    except Exception as e:
        logger.error(f"获取实验结果失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/analysis/<experiment_id>', methods=['GET'])
def get_statistical_analysis(experiment_id):
    """获取统计分析结果"""
    try:
        if experiment_id not in _experiment_results:
            return jsonify({
                'success': False,
                'error': '实验结果不存在'
            }), 404
        
        results = _experiment_results[experiment_id]
        
        # 执行统计分析
        from ....experiments.statistical_analysis import StatisticalAnalyzer
        analyzer = StatisticalAnalyzer()
        analysis = analyzer.analyze_experiment_results(results)
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logger.error(f"统计分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/charts/<experiment_id>', methods=['POST'])
def generate_experiment_charts(experiment_id):
    """生成实验图表"""
    try:
        if experiment_id not in _experiment_results:
            return jsonify({
                'success': False,
                'error': '实验结果不存在'
            }), 404
        
        data = request.get_json() or {}
        chart_types = data.get('chart_types', ['algorithm_comparison', 'performance_trend'])
        
        results = _experiment_results[experiment_id]
        
        # 生成图表
        from ....experiments.chart_generator import ChartGenerator
        generator = ChartGenerator()
        
        generated_files = []
        
        if 'algorithm_comparison' in chart_types:
            # 按算法分组结果
            results_by_algorithm = {}
            for result in results:
                if hasattr(result, 'config') and 'admission_config' in result.config:
                    algorithm = result.config['admission_config'].get('algorithm', 'unknown')
                    if algorithm not in results_by_algorithm:
                        results_by_algorithm[algorithm] = []
                    results_by_algorithm[algorithm].append(result)
            
            if len(results_by_algorithm) > 1:
                chart_file = generator.generate_algorithm_comparison_chart(results_by_algorithm)
                generated_files.append(chart_file)
        
        if 'performance_trend' in chart_types:
            chart_file = generator.generate_performance_trend_chart(results)
            generated_files.append(chart_file)
        
        if 'correlation_heatmap' in chart_types:
            chart_file = generator.generate_correlation_heatmap(results)
            generated_files.append(chart_file)
        
        return jsonify({
            'success': True,
            'data': {
                'generated_files': generated_files,
                'total_charts': len(generated_files)
            }
        })
        
    except Exception as e:
        logger.error(f"生成图表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/export/<experiment_id>', methods=['GET'])
def export_experiment_results(experiment_id):
    """导出实验结果"""
    try:
        if experiment_id not in _experiment_results:
            return jsonify({
                'success': False,
                'error': '实验结果不存在'
            }), 404
        
        results = _experiment_results[experiment_id]
        export_format = request.args.get('format', 'json')
        
        if export_format == 'json':
            # 导出JSON格式
            import tempfile
            import json
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                serializable_results = []
                for result in results:
                    if hasattr(result, '__dict__'):
                        serializable_results.append(result.__dict__)
                    else:
                        serializable_results.append(result)
                
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
                temp_file = f.name
            
            return send_file(
                temp_file,
                as_attachment=True,
                download_name=f"experiment_{experiment_id}_results.json",
                mimetype='application/json'
            )
        
        elif export_format == 'csv':
            # 导出CSV格式
            import pandas as pd
            import tempfile
            
            # 转换为DataFrame
            data = []
            for result in results:
                if hasattr(result, '__dict__'):
                    row = result.__dict__.copy()
                    # 展平嵌套字典
                    flat_row = {}
                    for key, value in row.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                flat_row[f"{key}_{sub_key}"] = sub_value
                        else:
                            flat_row[key] = value
                    data.append(flat_row)
            
            df = pd.DataFrame(data)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df.to_csv(f.name, index=False, encoding='utf-8-sig')
                temp_file = f.name
            
            return send_file(
                temp_file,
                as_attachment=True,
                download_name=f"experiment_{experiment_id}_results.csv",
                mimetype='text/csv'
            )
        
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的导出格式: {export_format}'
            }), 400
        
    except Exception as e:
        logger.error(f"导出实验结果失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/list', methods=['GET'])
def list_experiments():
    """列出所有实验"""
    try:
        experiments = []
        
        # 添加运行中的实验
        for exp_id, status in _running_experiments.items():
            experiments.append({
                'experiment_id': exp_id,
                'status': status['status'],
                'progress': status.get('progress', 0),
                'start_time': status.get('start_time'),
                'has_results': exp_id in _experiment_results
            })
        
        return jsonify({
            'success': True,
            'data': {
                'experiments': experiments,
                'total_experiments': len(experiments)
            }
        })
        
    except Exception as e:
        logger.error(f"列出实验失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/templates', methods=['GET'])
def get_experiment_templates():
    """获取实验模板"""
    try:
        from ....experiments.experiment_config import ExperimentConfigBuilder
        
        templates = {
            'baseline': ExperimentConfigBuilder.create_baseline_config().__dict__,
            'threshold': ExperimentConfigBuilder.create_threshold_config().__dict__,
            'positioning_aware': ExperimentConfigBuilder.create_positioning_aware_config().__dict__,
            'paper_experiments': [config.__dict__ for config in ExperimentConfigBuilder.create_paper_experiment_configs()[:5]],
            'comprehensive_ablation': ExperimentConfigBuilder.create_comprehensive_ablation_config().__dict__
        }
        
        return jsonify({
            'success': True,
            'data': templates
        })
    except Exception as e:
        logger.error(f"获取实验模板失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/charts/download', methods=['GET'])
def download_chart_file():
    """下载已生成的图表文件(PNG/CSV等)。"""
    try:
        file_path = request.args.get('file')
        if not file_path:
            return jsonify({'success': False, 'error': '缺少文件参数'}), 400

        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return jsonify({'success': False, 'error': '文件不存在'}), 404

        return send_file(str(p), as_attachment=True, download_name=p.name)
    except Exception as e:
        logger.error(f"下载图表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
