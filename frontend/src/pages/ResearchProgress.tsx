import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Progress, Spin, Timeline, Tag, Space, Typography, Button, Result,
} from 'antd';
import {
  LoadingOutlined, CheckCircleOutlined, ClockCircleOutlined,
  SyncOutlined, CloseCircleOutlined, ArrowLeftOutlined,
} from '@ant-design/icons';
import { getTaskStatus, getTaskLogs, TaskStatusResponse, LogEntry } from '../api/client';
import AgentPipeline from '../components/AgentPipeline';
import LogViewer from '../components/LogViewer';

const { Title, Text } = Typography;

const AGENT_STEPS = [
  { name: 'ChiefArchitect', display: '规划 Agent', desc: '理解任务，制定研究计划' },
  { name: 'DeepScout', display: '检索 Agent', desc: '多源信息检索与证据收集' },
  { name: 'DataAnalyst', display: '分析 Agent', desc: '数据查询与指标分析' },
  { name: 'CodeWizard', display: '图表 Agent', desc: '图表生成与可视化' },
  { name: 'LeadWriter', display: '撰写 Agent', desc: '中文研究报告撰写' },
  { name: 'CriticMaster', display: '评审 Agent', desc: '质量评审与路由决策' },
];

const ResearchProgress: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const completedRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    if (!taskId) return;
    try {
      const data = await getTaskStatus(taskId);
      setStatus(data);

      if ((data.status === 'completed' || data.status === 'complete') && !completedRef.current) {
        completedRef.current = true;
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        // Wait 3s for DB save to flush, then navigate
        setTimeout(() => navigate(`/result/${taskId}`), 3000);
      }

      if (data.status === 'error' || data.status === 'failed') {
        setError('研究任务执行失败');
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }, [taskId, navigate]);

  const fetchLogs = useCallback(async () => {
    if (!taskId) return;
    try {
      const data = await getTaskLogs(taskId);
      setLogs(Array.isArray(data) ? data : (data as any).logs || []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    fetchStatus();
    fetchLogs();
    pollingRef.current = setInterval(() => {
      fetchStatus();
      fetchLogs();
    }, 2000);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [taskId, fetchStatus, fetchLogs]);

  const getStatusTag = (s: string) => {
    switch (s) {
      case 'running': return <Tag icon={<SyncOutlined spin />} color="processing">执行中</Tag>;
      case 'completed':
      case 'complete': return <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>;
      case 'error':
      case 'failed': return <Tag icon={<CloseCircleOutlined />} color="error">失败</Tag>;
      default: return <Tag icon={<ClockCircleOutlined />} color="default">等待中</Tag>;
    }
  };

  const getProgress = () => {
    if (!status) return 0;
    // backend returns 0-100
    return Math.min(100, Math.max(0, status.progress));
  };

  const getCurrentAgent = () => {
    if (!status?.current_step) return null;
    const step = status.current_step;
    for (const a of AGENT_STEPS) {
      if (step.startsWith(a.name)) return a;
    }
    return null;
  };

  // Build agent status list from current_step
  const buildAgentList = () => {
    const currentStep = status?.current_step || '';
    const isComplete = status?.status === 'completed' || status?.status === 'complete';
    const stepOrder = AGENT_STEPS.map(a => a.name);

    // Find the active agent index
    let activeIdx = -1;
    for (let i = 0; i < stepOrder.length; i++) {
      if (currentStep.startsWith(stepOrder[i]) || currentStep.includes(stepOrder[i])) {
        activeIdx = i;
        break;
      }
    }
    // Also check for _complete suffixes
    if (activeIdx === -1) {
      for (let i = stepOrder.length - 1; i >= 0; i--) {
        if (currentStep.includes(stepOrder[i] + '_complete') || currentStep.includes('re_research') || currentStep.includes('revise')) {
          activeIdx = i;
          break;
        }
      }
    }

    return AGENT_STEPS.map((a, idx) => ({
      ...a,
      status: isComplete ? 'done' : idx < activeIdx ? 'done' : idx === activeIdx ? 'active' : 'pending',
    } as any));
  };

  if (error) {
    return (
      <Result status="error" title="研究任务失败" subTitle={error}
        extra={[<Button key="back" icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回首页</Button>]}
      />
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} type="text" />
              <Title level={4} style={{ margin: 0 }}>研究进度</Title>
              {status && getStatusTag(status.status)}
            </Space>
            {status && (
              <Text type="secondary">迭代次数: {status.iteration_count}</Text>
            )}
          </div>

          {status && getCurrentAgent() && (
            <Text type="secondary">当前: {getCurrentAgent()?.display}</Text>
          )}

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>总体进度</Text>
              <Text strong>{getProgress()}%</Text>
            </div>
            <Progress
              percent={getProgress()}
              status={status?.status === 'error' ? 'exception' : 'active'}
            />
          </div>
        </Space>
      </Card>

      <Card title="智能体协作流程" style={{ borderRadius: 12, marginBottom: 24 }}>
        <AgentPipeline agents={buildAgentList()} currentAgent={status?.current_step || ''} />
      </Card>

      <Card title="执行日志" style={{ borderRadius: 12 }}>
        <LogViewer logs={logs} />
      </Card>

      {(status?.status === 'completed' || status?.status === 'complete') && (
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Spin tip="研究完成，正在跳转到报告页面..." />
        </div>
      )}
    </div>
  );
};

export default ResearchProgress;
