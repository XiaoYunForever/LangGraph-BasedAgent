# checkpoint = find_checkpoint(
#     graph,
#     config,
#     lambda snapshot:
#     snapshot.next == ("writer",)
# )
#
# if checkpoint is None:
#     print("没有找到目标 checkpoint")
#     return
#
# print("\n" + "=" * 60)
# print("FOUND CHECKPOINT")
# print("=" * 60)
#
# print(
#     checkpoint.config
#     ["configurable"]
#     ["checkpoint_id"]
# )
#
# print("next =", checkpoint.next)
#
# print(
#     "completed =",
#     [
#         r["work_id"]
#         for r in checkpoint.values.get(
#         "task_results",
#         []
#     )
#     ]
# )
# # ================================================
# for chunk in graph.stream(
#         None,
#         config=checkpoint.config,
#         stream_mode="updates",
# ):
#     print("NEW", chunk)
#
# fork_config = graph.update_state(
#     checkpoint.config,
#     {
#         "wave": 99
#     }
# )
# print("\n" + "=" * 60)
# print("FORK FROM MODIFIED CHECKPOINT")
# print("=" * 60)
#
# for chunk in graph.stream(
#         None,
#         config=fork_config,
#         stream_mode="values",
# ):
#     print(chunk)