# Xiaosi PDF Routing Rules

## Scope

These rules match the current vault structure in `D:\obsidianNotes\小司\xiaosi`.

## Primary Series

- `趋势知识圈`:
  - route by issue number
  - `3`, `8` -> `2026/趋势知识圈/云南财经财务老师`
  - `4`, `9` -> `2026/趋势知识圈/新结构经济学老师`
  - `5`, `10` -> `2026/趋势知识圈/国际关系学院老师`
  - `6`, `11` -> `2026/趋势知识圈/陈鹏老师`
  - `7` -> `2026/趋势知识圈/记者`
  - `特邀课程` currently routes to `2026/趋势知识圈/陈鹏老师`

- `行业知识圈` main folders:
  - `宏观` -> `2026/宏观策略`
  - `半导体`, `芯片`, `存储`, `算力芯片`, `新兴产业` -> `2026/2026首席/半导体`
  - `新能源`, `电新`, `锂电`, `光伏`, `户储` -> `2026/2026首席/新能源`
  - `医药`, `创新药`, `小核酸`, `脑机接口` -> `2026/2026首席/医药`
  - `消费`, `轻工`, `纺织`, `服装` -> `2026/2026首席/消费`

- `买方知识圈`:
  - route to `2026/2026首席/市场策略`

## 加餐 Rules

- `刘涛加餐`, `刘涛老师加餐` -> `2026/2026首席加餐/市场策略`
- `岳老师加餐`, `岳云清老师加餐`:
  - AI-related titles -> `2026/2026首席加餐/AI`
  - medical-related titles -> `2026/2026首席加餐/医药`
  - market-strategy titles -> `2026/2026首席加餐/市场策略`

## Deduplication

- treat the same PDF as a duplicate when the target folder already contains a file with the same normalized signature and identical SHA256 hash
- in that case remove the downloaded duplicate from `Downloads` and keep the archived copy

## Escalation

- if a new title does not match any rule, inspect nearby archived files in the destination tree before moving it manually
- if the filename strongly suggests a new recurring category, update this skill
