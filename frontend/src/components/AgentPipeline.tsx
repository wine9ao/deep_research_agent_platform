import React from 'react';
import { Steps, Card, Typography, Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  UserSwitchOutlined,
  SearchOutlined,
  BarChartOutlined,
  CodeOutlined,
  EditOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import type { AgentStatus } from '../api/client';

const { Text } = Typography;

interface AgentPipelineProps {
  agents: AgentStatus[];
  currentAgent: string;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  ChiefArchitect: <UserSwitchOutlined />,
  DeepScout: <SearchOutlined />,
  DataAnalyst: <BarChartOutlined />,
  CodeWizard: <CodeOutlined />,
  LeadWriter: <EditOutlined />,
  CriticMaster: <AuditOutlined />,
};

const AGENT_COLORS: Record<string, string> = {
  ChiefArchitect: '#722ed1',
  DeepScout: '#1677ff',
  DataAnalyst: '#13c2c2',
  CodeWizard: '#52c41a',
  LeadWriter: '#fa8c16',
  CriticMaster: '#eb2f96',
};

const getAgentStatusIcon = (status: string) => {
  switch (status) {
    case 'active':
      return <LoadingOutlined style={{ color: '#1677ff' }} />;
    case 'done':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    default:
      return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
  }
};

const AgentPipeline: React.FC<AgentPipelineProps> = ({ agents, currentAgent }) => {
  if (!agents || agents.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
        等待智能体初始化...
      </div>
    );
  }

  return (
    <div>
      {/* Horizontal step indicators */}
      <Steps
        current={agents.filter((a) => a.status === 'done').length}
        size="small"
        style={{ marginBottom: 24 }}
        items={agents.map((agent) => ({
          title: agent.display_name,
          status: agent.status === 'done' ? 'finish' : agent.status === 'active' ? 'process' : 'wait',
          icon: agent.status === 'active' ? <LoadingOutlined /> : undefined,
        }))}
      />

      {/* Agent cards in a horizontal row */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          overflowX: 'auto',
          paddingBottom: 8,
        }}
      >
        {agents.map((agent) => {
          const isActive = agent.status === 'active';
          const isDone = agent.status === 'done';
          const color = AGENT_COLORS[agent.name] || '#d9d9d9';

          return (
            <Tooltip
              key={agent.name}
              title={
                <div>
                  <div>{agent.description}</div>
                  <div style={{ marginTop: 4 }}>
                    状态: {agent.status === 'active' ? '执行中' : agent.status === 'done' ? '已完成' : '等待中'}
                  </div>
                </div>
              }
            >
              <Card
                size="small"
                className={isActive ? 'agent-active' : ''}
                style={{
                  minWidth: 140,
                  flex: 1,
                  textAlign: 'center',
                  borderRadius: 10,
                  borderTop: `3px solid ${isActive ? color : isDone ? color : '#e8e8e8'}`,
                  opacity: isDone ? 1 : isActive ? 1 : 0.55,
                  background: isActive ? '#f0f5ff' : isDone ? '#f6ffed' : '#fff',
                  transition: 'all 0.3s ease',
                  cursor: 'default',
                }}
              >
                <div style={{ fontSize: 22, color: isActive ? color : isDone ? color : '#ccc', marginBottom: 8 }}>
                  {AGENT_ICONS[agent.name] || <ClockCircleOutlined />}
                </div>
                <Text strong style={{ display: 'block', fontSize: 13, marginBottom: 4 }}>
                  {agent.display_name}
                </Text>
                <div style={{ marginTop: 4 }}>
                  <Tag
                    color={isActive ? 'processing' : isDone ? 'success' : 'default'}
                    icon={isActive ? <LoadingOutlined /> : isDone ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
                    style={{ fontSize: 11 }}
                  >
                    {isActive ? '执行中' : isDone ? '完成' : '等待'}
                  </Tag>
                </div>
              </Card>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
};

export default AgentPipeline;
