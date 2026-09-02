import inspect
import frappe


def run():
    print("=" * 70)
    print("ACTUAL FRAPPE WORKSPACE CLASS")
    print("=" * 70)

    controller = frappe.get_controller("Workspace")

    print("\nCONTROLLER:")
    print(controller)

    print("\nCLASS:")
    print(controller.__class__)

    print("\nMODULE:")
    print(controller.__class__.__module__)

    print("\nMRO:")
    for cls in controller.__class__.__mro__:
        print(f"  {cls}")

    print("\n=== is_permitted LOOKUP ===")

    for cls in controller.__class__.__mro__:
        if "is_permitted" in cls.__dict__:
            print(f"\nFOUND IN: {cls}")
            print(inspect.getsource(cls.__dict__["is_permitted"]))
            break
    else:
        print("is_permitted not found in MRO")

    print("\n=== WORKSPACE CLASS SOURCE ===")

    try:
        print(inspect.getsource(controller.__class__))
    except Exception as e:
        print(f"SOURCE ERROR: {e}")

    print("\n" + "=" * 70)
    print("WORKSPACE CLASS INSPECTION COMPLETE")
    print("=" * 70)
