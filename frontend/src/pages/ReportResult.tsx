import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Tabs,
  Button,
  Space,
  Typography,
  Divider,
  Spin,
  Result,
  message,
} from 'antd';
import {
  DownloadOutlined,
  ArrowLeftOutlined,
  FileTextOutlined,
  BarChartOutlined,
  LinkOutlined,
  TrophyOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getTaskResult, TaskResultResponse } from '../api/client';
import ChartViewer from '../components/ChartViewer';
import SourceList from '../components/SourceList';
import QualityScoreCard from '../components/QualityScoreCard';

const { Title, Text } = Typography;

const ReportResult: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<TaskResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResult = async () => {
    if (!taskId) return;
    setLoading(true);
    setError(null);
    // Retry up to 3 times with 1s delay (DB may still be flushing)
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const data = await getTaskResult(taskId);
        if (data.final_report) {
          setResult(data);
          setLoading(false);
          return;
        }
      } catch (err: unknown) {
        if (attempt === 2) {
          const errorMessage = err instanceof Error ? err.message : '获取研究结果失败';
          setError(errorMessage);
        }
      }
      if (attempt < 2) {
        await new Promise(r => setTimeout(r, 1000));
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchResult();
  }, [taskId]);

  const handleDownloadMarkdown = () => {
    if (!result?.final_report) {
      message.warning('没有可下载的报告内容');
      return;
    }
    const blob = new Blob([result.final_report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `研究报告_${taskId || 'report'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success('报告下载成功');
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 120 }}>
        <Spin size="large" tip="正在加载研究报告..." />
      </div>
    );
  }

  if (error || !result) {
    return (
      <Result
        status="error"
        title="加载失败"
        subTitle={error || '未找到研究结果'}
        extra={[
          <Button key="retry" icon={<ReloadOutlined />} onClick={fetchResult}>
            重试
          </Button>,
          <Button
            key="back"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/')}
          >
            返回首页
          </Button>,
        ]}
      />
    );
  }

  const tabItems = [
    {
      key: 'report',
      label: (
        <span>
          <FileTextOutlined />
          研究报告
        </span>
      ),
      children: (
        <div
          className="markdown-body"
          style={{
            padding: '24px 32px',
            background: '#fff',
            borderRadius: 8,
            minHeight: 400,
          }}
        >
          {result.final_report ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.final_report}</ReactMarkdown>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
              <Text type="secondary">暂无报告内容</Text>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'charts',
      label: (
        <span>
          <BarChartOutlined />
          数据图表
          {result.charts && result.charts.length > 0 && (
            <span style={{ marginLeft: 4, fontSize: 12, color: '#999' }}>
              ({result.charts.length})
            </span>
          )}
        </span>
      ),
      children: (
        <div style={{ padding: 16 }}>
          {result.charts && result.charts.length > 0 ? (
            result.charts.map((chart, index) => (
              <Card
                key={index}
                title={chart.title || `图表 ${index + 1}`}
                style={{ marginBottom: 16, borderRadius: 8 }}
              >
                <ChartViewer option={chart.echarts_option} />
              </Card>
            ))
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
              <Text type="secondary">暂无图表数据</Text>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'sources',
      label: (
        <span>
          <LinkOutlined />
          引用来源
          {result.sources && result.sources.length > 0 && (
            <span style={{ marginLeft: 4, fontSize: 12, color: '#999' }}>
              ({result.sources.length})
            </span>
          )}
        </span>
      ),
      children: (
        <div style={{ padding: 16 }}>
          <SourceList sources={result.sources || []} />
        </div>
      ),
    },
    {
      key: 'quality',
      label: (
        <span>
          <TrophyOutlined />
          质量评分
        </span>
      ),
      children: (
        <div style={{ padding: 16 }}>
          {result.quality_scores ? (
            <QualityScoreCard scores={result.quality_scores} />
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
              <Text type="secondary">暂无质量评分数据</Text>
            </div>
          )}
        </div>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/')}
              type="text"
            />
            <Title level={4} style={{ margin: 0 }}>
              研究报告
            </Title>
          </Space>
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleDownloadMarkdown}
            >
              下载报告 (Markdown)
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchResult}
            >
              刷新
            </Button>
          </Space>
        </div>
        <Divider style={{ margin: '12px 0' }} />
        <Text type="secondary">任务 ID: {taskId}</Text>
        {result.quality_scores && (
          <Text type="secondary" style={{ marginLeft: 24 }}>
            综合评分: {result.quality_scores.final_score}/100
          </Text>
        )}
      </Card>

      {/* Content Tabs */}
      <Card style={{ borderRadius: 12 }} bodyStyle={{ padding: 0 }}>
        <Tabs
          defaultActiveKey="report"
          items={tabItems}
          style={{ padding: '0 0' }}
          tabBarStyle={{ padding: '0 24px', marginBottom: 0 }}
        />
      </Card>
    </div>
  );
};

export default ReportResult;
