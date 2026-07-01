import React from 'react';
import { Empty, Typography } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Text } = Typography;

interface ChartViewerProps {
  option: Record<string, unknown> | null;
  height?: number | string;
}

const ChartViewer: React.FC<ChartViewerProps> = ({ option, height = 400 }) => {
  if (!option || Object.keys(option).length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: typeof height === 'number' ? height : 400,
          background: '#fafafa',
          borderRadius: 8,
        }}
      >
        <Empty
          image={<BarChartOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
          description={<Text type="secondary">暂无图表数据</Text>}
        />
      </div>
    );
  }

  return (
    <div style={{ width: '100%' }}>
      <ReactECharts
        option={option}
        style={{ height: typeof height === 'number' ? height : 400, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
};

export default ChartViewer;
