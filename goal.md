请参考https://docs.bigmodel.cn/cn/coding-plan/best-practice/spec-kit和https://github.com/github/spec-kit
通过speckit来规划并完成需求：
我想通过WCL抓取魔兽世界时光服：武器战士的dps榜单。要求如下：
wcl参考链接：https://cn.warcraftlogs.com/
1、统计P3阶段纳克萨玛斯相关boss，每个boss单独统计，只取秒伤前三名的游戏ID
2、以表格形式输出结果。表头为：名字（游戏ID），秒伤，日期，用时
3、进一步抓取该角色的装备、技能释放、获取buff

先调用/speckit.specify

