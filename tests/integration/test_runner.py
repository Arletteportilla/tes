"""
Integration test runner for the Sistema de Polinización y Germinación.
Runs all integration tests and provides comprehensive reporting.
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_django():
    """Setup Django environment for testing."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_polinizacion.settings.test_settings')
    django.setup()


def run_integration_tests():
    """Run all integration tests."""
    setup_django()
    
    # Test modules to run
    test_modules = [
        'tests.integration.test_pollination_workflow',
        'tests.integration.test_germination_workflow', 
        'tests.integration.test_alerts_workflow',
        'tests.integration.test_reports_workflow',
        'tests.integration.test_permissions_security',
        'tests.integration.test_authentication_integration'
    ]
    
    print("=" * 80)
    print("RUNNING INTEGRATION TESTS FOR SISTEMA DE POLINIZACIÓN Y GERMINACIÓN")
    print("=" * 80)
    
    # Run tests with coverage if available
    try:
        import coverage
        cov = coverage.Coverage()
        cov.start()
        coverage_enabled = True
        print("Coverage tracking enabled")
    except ImportError:
        coverage_enabled = False
        print("Coverage not available - install with: pip install coverage")
    
    print(f"\nRunning {len(test_modules)} integration test modules:")
    for module in test_modules:
        print(f"  - {module}")
    
    print("\n" + "-" * 80)
    
    # Execute tests
    test_args = ['manage.py', 'test'] + test_modules + [
        '--verbosity=2',
        '--keepdb',  # Keep test database for faster subsequent runs
        '--parallel',  # Run tests in parallel
    ]
    
    try:
        execute_from_command_line(test_args)
        print("\n" + "=" * 80)
        print("INTEGRATION TESTS COMPLETED SUCCESSFULLY")
        
        if coverage_enabled:
            cov.stop()
            cov.save()
            
            print("\nCOVERAGE REPORT:")
            print("-" * 40)
            cov.report(show_missing=True)
            
            # Generate HTML coverage report
            cov.html_report(directory='htmlcov')
            print("\nHTML coverage report generated in 'htmlcov' directory")
        
        return True
        
    except SystemExit as e:
        print(f"\n" + "=" * 80)
        print(f"INTEGRATION TESTS FAILED WITH EXIT CODE: {e.code}")
        
        if coverage_enabled:
            cov.stop()
            cov.save()
        
        return False


def run_specific_workflow_test(workflow_name):
    """Run tests for a specific workflow."""
    setup_django()
    
    workflow_modules = {
        'pollination': 'tests.integration.test_pollination_workflow',
        'germination': 'tests.integration.test_germination_workflow',
        'alerts': 'tests.integration.test_alerts_workflow',
        'reports': 'tests.integration.test_reports_workflow',
        'permissions': 'tests.integration.test_permissions_security',
        'authentication': 'tests.integration.test_authentication_integration'
    }
    
    if workflow_name not in workflow_modules:
        print(f"Unknown workflow: {workflow_name}")
        print(f"Available workflows: {', '.join(workflow_modules.keys())}")
        return False
    
    module = workflow_modules[workflow_name]
    print(f"Running {workflow_name} workflow tests: {module}")
    
    test_args = ['manage.py', 'test', module, '--verbosity=2']
    
    try:
        execute_from_command_line(test_args)
        return True
    except SystemExit as e:
        print(f"Tests failed with exit code: {e.code}")
        return False


def run_performance_tests():
    """Run performance-focused integration tests."""
    setup_django()
    
    print("Running performance-focused integration tests...")
    
    # Focus on tests that check performance
    performance_test_patterns = [
        'test_*_performance*',
        'test_*_large_dataset*',
        'test_*_bulk_*'
    ]
    
    test_args = ['manage.py', 'test', 'tests.integration', '--verbosity=2'] + [
        f'--pattern={pattern}' for pattern in performance_test_patterns
    ]
    
    try:
        execute_from_command_line(test_args)
        return True
    except SystemExit as e:
        print(f"Performance tests failed with exit code: {e.code}")
        return False


def run_security_tests():
    """Run security-focused integration tests."""
    setup_django()
    
    print("Running security-focused integration tests...")
    
    test_args = [
        'manage.py', 'test', 
        'tests.integration.test_permissions_security',
        'tests.integration.test_authentication_integration',
        '--verbosity=2'
    ]
    
    try:
        execute_from_command_line(test_args)
        return True
    except SystemExit as e:
        print(f"Security tests failed with exit code: {e.code}")
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'all':
            success = run_integration_tests()
        elif command == 'performance':
            success = run_performance_tests()
        elif command == 'security':
            success = run_security_tests()
        elif command in ['pollination', 'germination', 'alerts', 'reports', 'permissions', 'authentication']:
            success = run_specific_workflow_test(command)
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  all          - Run all integration tests")
            print("  performance  - Run performance tests")
            print("  security     - Run security tests")
            print("  pollination  - Run pollination workflow tests")
            print("  germination  - Run germination workflow tests")
            print("  alerts       - Run alerts workflow tests")
            print("  reports      - Run reports workflow tests")
            print("  permissions  - Run permissions tests")
            print("  authentication - Run authentication tests")
            success = False
    else:
        success = run_integration_tests()
    
    sys.exit(0 if success else 1)