"""
事件调度器

管理仿真中的各种事件
"""

import heapq
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Event:
    """仿真事件"""
    time: float
    event_type: str
    data: Dict[str, Any]
    priority: int = 0  # 优先级，数字越小优先级越高
    
    def __lt__(self, other):
        """用于堆排序的比较函数"""
        if self.time != other.time:
            return self.time < other.time
        return self.priority < other.priority


class EventScheduler:
    """事件调度器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 事件队列（最小堆）
        self.event_queue: List[Event] = []
        
        # 事件统计
        self.total_events = 0
        self.processed_events = 0
        self.event_type_counts = {}
        
        self.logger.info("事件调度器初始化完成")
    
    def schedule_event(self, 
                      time: float, 
                      event_type: str, 
                      data: Dict[str, Any], 
                      priority: int = 0):
        """调度一个事件"""
        event = Event(
            time=time,
            event_type=event_type,
            data=data,
            priority=priority
        )
        
        heapq.heappush(self.event_queue, event)
        self.total_events += 1
        
        # 更新统计
        if event_type not in self.event_type_counts:
            self.event_type_counts[event_type] = 0
        self.event_type_counts[event_type] += 1
        
        self.logger.debug(f"调度事件: {event_type} @ t={time:.2f}")
    
    def get_events(self, current_time: float) -> List[Dict[str, Any]]:
        """获取当前时间应该处理的所有事件"""
        events_to_process = []
        
        # 从堆中取出所有到期的事件
        while self.event_queue and self.event_queue[0].time <= current_time:
            event = heapq.heappop(self.event_queue)
            events_to_process.append({
                'type': event.event_type,
                'data': event.data,
                'time': event.time,
                'priority': event.priority
            })
            self.processed_events += 1
        
        if events_to_process:
            self.logger.debug(f"处理{len(events_to_process)}个事件 @ t={current_time:.2f}")
        
        return events_to_process
    
    def peek_next_event_time(self) -> Optional[float]:
        """查看下一个事件的时间"""
        if self.event_queue:
            return self.event_queue[0].time
        return None
    
    def cancel_events(self, event_type: Optional[str] = None, 
                     filter_func: Optional[callable] = None):
        """取消事件"""
        if event_type is None and filter_func is None:
            # 取消所有事件
            cancelled_count = len(self.event_queue)
            self.event_queue.clear()
            self.logger.info(f"取消了{cancelled_count}个事件")
            return cancelled_count
        
        # 过滤事件
        new_queue = []
        cancelled_count = 0
        
        for event in self.event_queue:
            should_cancel = False
            
            if event_type and event.event_type == event_type:
                should_cancel = True
            
            if filter_func and filter_func(event):
                should_cancel = True
            
            if should_cancel:
                cancelled_count += 1
            else:
                new_queue.append(event)
        
        # 重建堆
        self.event_queue = new_queue
        heapq.heapify(self.event_queue)
        
        if cancelled_count > 0:
            self.logger.info(f"取消了{cancelled_count}个事件")
        
        return cancelled_count
    
    def schedule_periodic_event(self, 
                              start_time: float,
                              interval: float,
                              event_type: str,
                              data: Dict[str, Any],
                              end_time: Optional[float] = None,
                              max_occurrences: Optional[int] = None):
        """调度周期性事件"""
        current_time = start_time
        occurrence_count = 0
        
        while True:
            # 检查结束条件
            if end_time and current_time > end_time:
                break
            
            if max_occurrences and occurrence_count >= max_occurrences:
                break
            
            # 调度事件
            event_data = data.copy()
            event_data['occurrence'] = occurrence_count
            event_data['is_periodic'] = True
            
            self.schedule_event(current_time, event_type, event_data)
            
            # 更新时间和计数
            current_time += interval
            occurrence_count += 1
        
        self.logger.info(f"调度了{occurrence_count}个周期性事件: {event_type}")
    
    def schedule_batch_events(self, events: List[Dict[str, Any]]):
        """批量调度事件"""
        for event_info in events:
            self.schedule_event(
                time=event_info['time'],
                event_type=event_info['type'],
                data=event_info.get('data', {}),
                priority=event_info.get('priority', 0)
            )
        
        self.logger.info(f"批量调度了{len(events)}个事件")
    
    def get_pending_events_count(self) -> int:
        """获取待处理事件数量"""
        return len(self.event_queue)
    
    def get_events_by_type(self, event_type: str) -> List[Event]:
        """获取指定类型的所有待处理事件"""
        return [event for event in self.event_queue if event.event_type == event_type]
    
    def get_events_in_time_range(self, start_time: float, end_time: float) -> List[Event]:
        """获取指定时间范围内的事件"""
        return [event for event in self.event_queue 
                if start_time <= event.time <= end_time]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取事件调度统计"""
        return {
            'total_events': self.total_events,
            'processed_events': self.processed_events,
            'pending_events': len(self.event_queue),
            'event_type_counts': self.event_type_counts.copy(),
            'next_event_time': self.peek_next_event_time()
        }
    
    def clear(self):
        """清空所有事件"""
        self.event_queue.clear()
        self.total_events = 0
        self.processed_events = 0
        self.event_type_counts.clear()
        self.logger.info("事件调度器已清空")
    
    def export_events(self) -> List[Dict[str, Any]]:
        """导出所有待处理事件"""
        return [
            {
                'time': event.time,
                'type': event.event_type,
                'data': event.data,
                'priority': event.priority
            }
            for event in sorted(self.event_queue, key=lambda x: x.time)
        ]
    
    def import_events(self, events: List[Dict[str, Any]]):
        """导入事件"""
        self.clear()
        
        for event_info in events:
            self.schedule_event(
                time=event_info['time'],
                event_type=event_info['type'],
                data=event_info['data'],
                priority=event_info.get('priority', 0)
            )
        
        self.logger.info(f"导入了{len(events)}个事件")
    
    def debug_print_queue(self, max_events: int = 10):
        """调试：打印事件队列"""
        self.logger.debug("事件队列状态:")
        
        sorted_events = sorted(self.event_queue, key=lambda x: x.time)
        for i, event in enumerate(sorted_events[:max_events]):
            self.logger.debug(f"  {i+1}. t={event.time:.2f}, type={event.event_type}, "
                            f"priority={event.priority}")
        
        if len(sorted_events) > max_events:
            self.logger.debug(f"  ... 还有{len(sorted_events) - max_events}个事件")
    
    def validate_queue(self) -> bool:
        """验证事件队列的完整性"""
        try:
            # 检查堆属性
            for i in range(len(self.event_queue)):
                left_child = 2 * i + 1
                right_child = 2 * i + 2
                
                if left_child < len(self.event_queue):
                    if self.event_queue[i] > self.event_queue[left_child]:
                        self.logger.error(f"堆属性违反: 父节点{i} > 左子节点{left_child}")
                        return False
                
                if right_child < len(self.event_queue):
                    if self.event_queue[i] > self.event_queue[right_child]:
                        self.logger.error(f"堆属性违反: 父节点{i} > 右子节点{right_child}")
                        return False
            
            self.logger.debug("事件队列验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"事件队列验证失败: {e}")
            return False
