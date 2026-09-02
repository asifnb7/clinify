import inspect
import frappe


def run():
    print("=" * 70)
    print("FRAPPE WORKSPACE ACCESS LOGIC")
    print("=" * 70)

    modules = [
        "frappe.desk.workspace",
        "frappe.desk.doctype.workspace.workspace",
    ]

    for module_name in modules:
        print("")
        print("=" * 70)
        print(f"MODULE: {module_name}")
        print("=" * 70)

        try:
            module = __import__(
                module_name,
                fromlist=["*"],
            )
        except Exception as e:
            print(f"IMPORT ERROR: {e}")
            continue

        for name in (
            "get_workspace_sidebar_items",
            "get_workspace",
            "get_workspaces",
            "get_workspace_access",
            "has_permission",
        ):
            if hasattr(module, name):
                obj = getattr(module, name)

                print("")
                print(f"--- {name} ---")

                try:
                    print(inspect.getsource(obj))
                except Exception as e:
                    print(f"SOURCE ERROR: {e}")

    print("")
    print("=" * 70)
    print("WORKSPACE ACCESS LOGIC INSPECTION COMPLETE")
    print("=" * 70)
