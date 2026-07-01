import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Input,
  Select,
  Switch,
  Button,
  Typography,
  Space,
  Tag,
  Row,
  Col,
  message,
} from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { createResearch, runResearch } from '../api/client';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const RESEARCH_TYPES = [
  { value: '行业分析', label: '行业分析' },
  { value: '公司分析', label: '公司分析' },
  { value: '财务分析', label: '财务分析' },
  { value: '竞品分析', label: '竞品分析' },
  { value: '政策分析', label: '政策分析' },
  { value: '综合研究', label: '综合研究' },
];

const EXAMPLE_QUERIES = [
  {
    title: '新能源汽车行业发展趋势',
    type: '行业分析',
    query: '分析2024-2026年中国新能源汽车行业的发展趋势、竞争格局和主要机遇',
  },
  {
    title: '英伟达公司深度分析',
    type: '公司分析',
    query: '请对英伟达(NVIDIA)进行深度分析，包括其业务模式、财务状况、核心竞争力以及在AI芯片领域的市场地位',
  },
  {
    title: '中国AI政策环境研究',
    type: '政策分析',
    query: '研究中国2024-2025年人工智能相关政策，分析政策对产业发展的影响和未来的政策走向',
  },
];

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [researchType, setResearchType] = useState('综合研究');
  const [useMock, setUseMock] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleStartResearch = async () => {
    if (!query.trim()) {
      message.warning('请输入研究问题');
      return;
    }

    setLoading(true);
    try {
      const createRes = await createResearch(query.trim(), researchType, useMock);
      const taskId = createRes.task_id;

      // Start research in background
      runResearch(taskId).catch((err) => {
        console.error('Failed to start research:', err);
      });

      message.success('研究任务已创建，正在跳转...');
      navigate(`/research/${taskId}`);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : '创建研究任务失败，请检查后端服务是否运行';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (example: (typeof EXAMPLE_QUERIES)[0]) => {
    setQuery(example.query);
    setResearchType(example.type);
  };

  return (
    <div>
      {/* Hero Section */}
      <div
        style={{
          textAlign: 'center',
          padding: '48px 24px 36px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderRadius: 16,
          marginBottom: 32,
          color: '#fff',
        }}
      >
        <Title level={1} style={{ color: '#fff', marginBottom: 8, fontSize: 40 }}>
          Deep Research Agent Platform
        </Title>
        <Title level={3} style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 400, marginBottom: 0 }}>
          多智能体协作 | 深度研究 | 自动报告生成
        </Title>
        <Paragraph
          style={{
            color: 'rgba(255,255,255,0.7)',
            fontSize: 16,
            maxWidth: 600,
            margin: '16px auto 0',
          }}
        >
          由6个专业AI智能体协同工作，从搜索、分析到报告撰写，
          全流程自动化完成深度研究任务
        </Paragraph>
      </div>

      {/* Main Research Card */}
      <Card
        style={{
          borderRadius: 12,
          boxShadow: '0 2px 16px rgba(0,0,0,0.06)',
          marginBottom: 32,
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: 16 }}>
              <SearchOutlined style={{ marginRight: 8 }} />
              研究问题
            </Text>
            <TextArea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="请输入您想要深入研究的问题，例如：分析2024年中国人工智能行业的发展趋势..."
              autoSize={{ minRows: 3, maxRows: 6 }}
              style={{ marginTop: 8, fontSize: 15 }}
            />
          </div>

          <Row gutter={24} align="middle">
            <Col xs={24} sm={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>研究类型</Text>
                <Select
                  value={researchType}
                  onChange={setResearchType}
                  options={RESEARCH_TYPES}
                  style={{ width: '100%' }}
                  size="large"
                />
              </Space>
            </Col>
            <Col xs={24} sm={8}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>Mock 模式</Text>
                <div style={{ marginTop: 4 }}>
                  <Space>
                    <Switch
                      checked={useMock}
                      onChange={setUseMock}
                    />
                    <Text type="secondary">
                      {useMock ? '使用模拟数据' : '使用真实数据'}
                    </Text>
                  </Space>
                </div>
              </Space>
            </Col>
            <Col xs={24} sm={8}>
              <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={handleStartResearch}
                loading={loading}
                block
                style={{ height: 48, fontSize: 16, marginTop: 24 }}
              >
                开始研究
              </Button>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* Agent Architecture Overview */}
      <Card
        title={
          <Space>
            <ExperimentOutlined />
            <span>多智能体协作架构</span>
          </Space>
        }
        style={{ borderRadius: 12, marginBottom: 32 }}
      >
        <Row gutter={[16, 16]}>
          {[
            {
              name: 'ChiefArchitect',
              display: '首席架构师',
              desc: '任务分解与规划',
              color: '#722ed1',
            },
            {
              name: 'DeepScout',
              display: '深度侦察员',
              desc: '信息搜索与采集',
              color: '#1677ff',
            },
            {
              name: 'DataAnalyst',
              display: '数据分析师',
              desc: '数据处理与分析',
              color: '#13c2c2',
            },
            {
              name: 'CodeWizard',
              display: '代码巫师',
              desc: '可视化与计算',
              color: '#52c41a',
            },
            {
              name: 'LeadWriter',
              display: '首席撰稿人',
              desc: '报告撰写与整合',
              color: '#fa8c16',
            },
            {
              name: 'CriticMaster',
              display: '评审大师',
              desc: '质量审核与优化',
              color: '#eb2f96',
            },
          ].map((agent) => (
            <Col xs={12} sm={8} md={4} key={agent.name}>
              <Card
                size="small"
                style={{
                  textAlign: 'center',
                  borderTop: `3px solid ${agent.color}`,
                  borderRadius: 8,
                  height: '100%',
                }}
              >
                <Text strong style={{ display: 'block', fontSize: 14 }}>
                  {agent.display}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {agent.desc}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Example Queries */}
      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            <span>示例研究问题</span>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        <Row gutter={[16, 16]}>
          {EXAMPLE_QUERIES.map((example, index) => (
            <Col xs={24} sm={12} md={8} key={index}>
              <Card
                hoverable
                size="small"
                onClick={() => handleExampleClick(example)}
                style={{ borderRadius: 8, height: '100%' }}
              >
                <Space direction="vertical" size={4}>
                  <Space>
                    <Text strong>{example.title}</Text>
                    <Tag color="blue">{example.type}</Tag>
                  </Space>
                  <Text
                    type="secondary"
                    style={{ fontSize: 13 }}
                    ellipsis={{ rows: 2 }}
                  >
                    {example.query}
                  </Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
};

export default Home;
