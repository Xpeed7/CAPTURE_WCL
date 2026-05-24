"""WCL V2 GraphQL 查询语句"""

# 查询所有 zones，找到 Naxxramas 的 encounters 和 partitions
FIND_NAXX_QUERY = """
query {
  worldData {
    zones {
      id
      name
      encounters {
        id
        name
      }
    }
  }
}
"""

# 查询指定 zone 的 partitions
GET_PARTITIONS_QUERY = """
query ($zoneId: Int!) {
  worldData {
    zone(id: $zoneId) {
      id
      name
      partitions {
        id
        name
        default
      }
    }
  }
}
"""

# 查询指定 encounter 的武器战士 DPS 排名
# characterRankings 返回 JSON 标量，不能有子字段选择
GET_RANKINGS_QUERY = """
query (
  $encounterId: Int!
  $specName: String
  $className: String
  $metric: CharacterRankingMetricType
  $serverRegion: String
  $partition: Int
  $bracket: Int
) {
  worldData {
    encounter(id: $encounterId) {
      id
      name
      characterRankings(
        specName: $specName
        className: $className
        metric: $metric
        serverRegion: $serverRegion
        partition: $partition
        bracket: $bracket
        page: 1
      )
    }
  }
}
"""

# 查询 report 的 masterData 获取 actor (sourceID) 列表
GET_MASTER_DATA_QUERY = """
query ($code: String!) {
  reportData {
    report(code: $code) {
      masterData {
        abilities {
          gameID
          name
        }
        actors {
          id
          name
          type
        }
      }
    }
  }
}
"""

# 查询角色的装备详情
GET_PLAYER_DETAILS_QUERY = """
query ($code: String!, $fightIds: [Int]!) {
  reportData {
    report(code: $code) {
      playerDetails(
        fightIDs: $fightIds
        includeCombatantInfo: true
      )
    }
  }
}
"""

# 查询角色的技能释放（使用 events 端点获取明细事件）
GET_CASTS_QUERY = """
query (
  $code: String!
  $fightIds: [Int]!
  $sourceId: Int
  $startTime: Float
  $endTime: Float
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIds
        dataType: Casts
        sourceID: $sourceId
        startTime: $startTime
        endTime: $endTime
        translate: true
        limit: 1000
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""

# 查询角色获取的 Buff（使用 table 端点）
GET_BUFFS_QUERY = """
query ($code: String!, $fightIds: [Int]!, $sourceId: Int) {
  reportData {
    report(code: $code) {
      table(fightIDs: $fightIds, dataType: Buffs, sourceID: $sourceId)
    }
  }
}
"""

# 查询 report 的 fights 信息（获取时间范围）
GET_FIGHTS_QUERY = """
query ($code: String!, $fightIds: [Int]) {
  reportData {
    report(code: $code) {
      fights(fightIDs: $fightIds, translate: true) {
        id
        name
        startTime
        endTime
        bossPercentage
        encounterID
      }
    }
  }
}
"""
