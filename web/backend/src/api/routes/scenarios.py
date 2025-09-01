"""
场景管理API路由
"""

import logging
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError

scenarios_bp = Blueprint('scenarios', __name__)
logger = logging.getLogger(__name__)


class ScenarioSchema(Schema):
    """场景验证模式"""
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    durationSeconds = fields.Float(required=True, validate=lambda x: x > 0)
    trafficPattern = fields.Str(required=True)
    constellationConfig = fields.Dict(required=True)
    admissionConfig = fields.Dict(required=True)
    dsroqConfig = fields.Dict(required=True)
    positioningConfig = fields.Dict(required=True)
    simulationConfig = fields.Dict(required=True)
    expectedResults = fields.Dict(missing=dict)
    tags = fields.List(fields.Str(), missing=list)


@scenarios_bp.route('', methods=['GET'])
def get_all_scenarios():
    """获取所有场景"""
    try:
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 获取所有场景名称
        scenario_names = scenario_manager.list_scenarios()
        
        # 获取场景详情
        scenarios = []
        for name in scenario_names:
            scenario = scenario_manager.get_scenario(name)
            if scenario:
                summary = scenario_manager.get_scenario_summary(scenario)
                scenarios.append(summary)
        
        return jsonify({
            'success': True,
            'data': scenarios
        })
        
    except Exception as e:
        logger.error(f"获取场景列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('/<scenario_name>', methods=['GET'])
def get_scenario(scenario_name):
    """获取特定场景"""
    try:
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 获取场景
        scenario = scenario_manager.get_scenario(scenario_name)
        if not scenario:
            return jsonify({
                'success': False,
                'error': f'场景不存在: {scenario_name}'
            }), 404
        
        # 转换为字典格式
        from dataclasses import asdict
        scenario_dict = asdict(scenario)
        
        return jsonify({
            'success': True,
            'data': scenario_dict
        })
        
    except Exception as e:
        logger.error(f"获取场景失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('', methods=['POST'])
def create_scenario():
    """创建新场景"""
    try:
        # 验证请求数据
        schema = ScenarioSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 检查场景是否已存在
        existing_scenario = scenario_manager.get_scenario(data['name'])
        if existing_scenario:
            return jsonify({
                'success': False,
                'error': f'场景已存在: {data["name"]}'
            }), 409
        
        # 创建场景对象
        from src.simulation.scenario_manager import SimulationScenario
        scenario = SimulationScenario(
            name=data['name'],
            description=data['description'],
            duration_seconds=data['durationSeconds'],
            traffic_pattern=data['trafficPattern'],
            constellation_config=data['constellationConfig'],
            admission_config=data['admissionConfig'],
            dsroq_config=data['dsroqConfig'],
            positioning_config=data['positioningConfig'],
            simulation_config=data['simulationConfig'],
            expected_results=data.get('expectedResults'),
            tags=data.get('tags', [])
        )
        
        # 验证场景
        errors = scenario_manager.validate_scenario(scenario)
        if errors:
            return jsonify({
                'success': False,
                'error': '场景验证失败',
                'details': errors
            }), 400
        
        # 保存场景
        success = scenario_manager.save_scenario(scenario)
        if not success:
            return jsonify({
                'success': False,
                'error': '保存场景失败'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'场景创建成功: {data["name"]}'
        })
        
    except Exception as e:
        logger.error(f"创建场景失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('/<scenario_name>', methods=['PUT'])
def update_scenario(scenario_name):
    """更新场景"""
    try:
        # 验证请求数据
        schema = ScenarioSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 检查场景是否存在
        existing_scenario = scenario_manager.get_scenario(scenario_name)
        if not existing_scenario:
            return jsonify({
                'success': False,
                'error': f'场景不存在: {scenario_name}'
            }), 404
        
        # 更新场景对象
        from src.simulation.scenario_manager import SimulationScenario
        scenario = SimulationScenario(
            name=data['name'],
            description=data['description'],
            duration_seconds=data['durationSeconds'],
            traffic_pattern=data['trafficPattern'],
            constellation_config=data['constellationConfig'],
            admission_config=data['admissionConfig'],
            dsroq_config=data['dsroqConfig'],
            positioning_config=data['positioningConfig'],
            simulation_config=data['simulationConfig'],
            expected_results=data.get('expectedResults'),
            tags=data.get('tags', [])
        )
        
        # 验证场景
        errors = scenario_manager.validate_scenario(scenario)
        if errors:
            return jsonify({
                'success': False,
                'error': '场景验证失败',
                'details': errors
            }), 400
        
        # 保存场景
        success = scenario_manager.save_scenario(scenario)
        if not success:
            return jsonify({
                'success': False,
                'error': '保存场景失败'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'场景更新成功: {scenario_name}'
        })
        
    except Exception as e:
        logger.error(f"更新场景失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('/<scenario_name>', methods=['DELETE'])
def delete_scenario(scenario_name):
    """删除场景"""
    try:
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 检查场景是否存在
        existing_scenario = scenario_manager.get_scenario(scenario_name)
        if not existing_scenario:
            return jsonify({
                'success': False,
                'error': f'场景不存在: {scenario_name}'
            }), 404
        
        # 检查是否为预定义场景
        predefined_scenarios = [s.name for s in scenario_manager.predefined_scenarios]
        if scenario_name in predefined_scenarios:
            return jsonify({
                'success': False,
                'error': '无法删除预定义场景'
            }), 400
        
        # 删除场景文件
        import os
        scenario_file = scenario_manager.scenarios_dir / f"{scenario_name}.json"
        if scenario_file.exists():
            os.remove(scenario_file)
        
        # 从已加载场景中移除
        if scenario_name in scenario_manager.loaded_scenarios:
            del scenario_manager.loaded_scenarios[scenario_name]
        
        return jsonify({
            'success': True,
            'message': f'场景删除成功: {scenario_name}'
        })
        
    except Exception as e:
        logger.error(f"删除场景失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('/validate', methods=['POST'])
def validate_scenario():
    """验证场景配置"""
    try:
        # 验证请求数据
        schema = ScenarioSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 创建场景对象
        from src.simulation.scenario_manager import SimulationScenario
        scenario = SimulationScenario(
            name=data['name'],
            description=data['description'],
            duration_seconds=data['durationSeconds'],
            traffic_pattern=data['trafficPattern'],
            constellation_config=data['constellationConfig'],
            admission_config=data['admissionConfig'],
            dsroq_config=data['dsroqConfig'],
            positioning_config=data['positioningConfig'],
            simulation_config=data['simulationConfig'],
            expected_results=data.get('expectedResults'),
            tags=data.get('tags', [])
        )
        
        # 验证场景
        errors = scenario_manager.validate_scenario(scenario)
        
        return jsonify({
            'success': True,
            'data': {
                'valid': len(errors) == 0,
                'errors': errors
            }
        })
        
    except Exception as e:
        logger.error(f"验证场景失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scenarios_bp.route('/tags', methods=['GET'])
def get_scenario_tags():
    """获取所有场景标签"""
    try:
        # 获取场景管理器
        from src.simulation.scenario_manager import ScenarioManager
        scenario_manager = ScenarioManager()
        
        # 收集所有标签
        all_tags = set()
        
        # 预定义场景标签
        for scenario in scenario_manager.predefined_scenarios:
            if scenario.tags:
                all_tags.update(scenario.tags)
        
        # 已加载场景标签
        for scenario in scenario_manager.loaded_scenarios.values():
            if scenario.tags:
                all_tags.update(scenario.tags)
        
        return jsonify({
            'success': True,
            'data': sorted(list(all_tags))
        })
        
    except Exception as e:
        logger.error(f"获取场景标签失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
