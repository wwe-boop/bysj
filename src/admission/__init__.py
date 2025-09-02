"""
准入控制模块

该模块实现了LEO卫星网络的智能准入控制功能，包括：
- DRL基础的准入控制
- 阈值基础的准入控制
- ~~定位感知的准入控制~~ (功能已整合入DRL)
- 准入决策接口
"""

# 为避免在包导入时触发重依赖（如 gymnasium、SB3），此处不做子模块的强导入。
# 下游应直接从具体子模块导入：
#   from src.admission.admission_controller import AdmissionController
#   from src.admission.threshold_admission import ThresholdAdmissionController
#   from src.admission.drl_admission import DRLAdmissionController

__all__ = [
    # 暴露子模块名称，避免 "from src.admission import *" 时拉起重依赖
    'admission_controller',
    'threshold_admission',
    'drl_admission',
]
