#!/usr/bin/env python3

import asyncio
import logging
import unittest
from configparser import ConfigParser

from GridPi.lib import gridpi_core
from GridPi.lib.models import model_core
from GridPi.lib.process import process_core, process_graph, process_plugins

class TestProcessModule(unittest.TestCase):
    def setUp(self):
        "Setup for process Module Testing"
        self.test_system = gridpi_core.System()  # Create System container object

        # configure asset models
        self.parser = ConfigParser()
        self.parser.read_dict({'FEEDER':
                                   {'class_name': 'VirtualFeeder',
                                    'name': 'feeder'},
                               'ENERGY_STORAGE':
                                   {'class_name': 'VirtualEnergyStorage',
                                    'name': 'inverter'},
                               'GRID_INTERTIE':
                                   {'class_name': 'VirtualGridIntertie',
                                    'name': 'grid'}})

        asset_factory = model_core.AssetFactory()  # Create Asset Factory object
        for cfg in self.parser.sections():  # Add models to System, The asset factory acts on a configuration
            self.test_system.add_asset(asset_factory.factory(self.parser[cfg]))
        del asset_factory

        # configure processes
        self.parser.clear()
        self.parser.read_dict({'process_1': {'class_name': 'EssUpdateStatus'},
                               'process_2': {'class_name': 'GridUpdateStatus'},
                               'process_3': {'class_name': 'EssSocPowerController',
                                             'inverter_target_soc': 0.6},
                               'process_4': {'class_name': 'EssDemandLimitPowerController',
                                             'grid_kw_import_limit': 20,
                                             'grid_kw_export_limit': 20},
                               'process_5': {'class_name': 'EssWriteControl'}})
        process_factory = process_core.ProcessFactory()
        for cfg in self.parser.sections():
            self.test_system.add_process(process_factory.factory(self.parser[cfg]))
        del process_factory

        self.test_system.process.sort()

        # Get an asyncio event loop so that we can run updateStatus() and updateCtrl() on assets.
        self.loop = asyncio.get_event_loop()

    def test_process_factory(self):
        """ To test if the process factory returns an object of the desired class
        """
        logging.debug('********** Test process: test_process_factory **********')

        self.parser.clear()
        self.parser.read_dict({'test_process': {'class_name': 'EssSocPowerController',
                                                'some_special_attribute': 0.6}})

        PF = process_core.ProcessFactory()
        test_class = PF.factory(self.parser['test_process'])

        self.assertIsInstance(test_class, process_plugins.EssSocPowerController)
        #self.assertEqual(test_class.config['some_special_attribute'], 0.6)

    def test_tag_aggregation(self):
        ''' Test the tag aggregation class constructor aggregates two classes with similar outputs

        '''
        logging.debug('********** Test process: test_tag_aggregation **********')
        tag = 'inverter_kw_setpoint'

        inv_soc_pwr_ctrl_config = {
            "class_name": 'EssSocPowerController',
            "inverter_target_soc": 0.5,
            "target_inveter": 'inverter'
        }

        inv_dmdlmt_pwr_ctrl_config = {
            "class_name": 'EssDemandLimitPowerController',
            "grid_kw_import_limit": 10,
            "grid_kw_export_limit": 10,
            "target_inverter": 'inverter',
            "target_grid_intertie": 'grid'
        }

        inv_soc_pwr_ctrl = process_plugins.EssSocPowerController(inv_soc_pwr_ctrl_config)
        inv_dmdlmt_pwr_ctrl = process_plugins.EssDemandLimitPowerController(inv_dmdlmt_pwr_ctrl_config)

        process_list = [inv_soc_pwr_ctrl, inv_dmdlmt_pwr_ctrl]
        inv_pwr_ctrl_agg = process_plugins.AggregateProcessSummation(process_list)

        # Aggregate object is created
        self.assertIsInstance(inv_pwr_ctrl_agg, process_core.AggregateProcess)

        # Aggregate object composed of given objects
        self.assertIsInstance(inv_pwr_ctrl_agg._process_list[0], process_plugins.EssSocPowerController)
        self.assertIsInstance(inv_pwr_ctrl_agg._process_list[1], process_plugins.EssDemandLimitPowerController)

    def test_process(self):
        logging.debug('********** Test process: test_process **********')
        """ To test if data can be brought onto the tagbus from an asset, processed, and written back to the asset
        """

        # run updateStatus() twice. virtual components first update is an initializion state, then they begin to report.
        for x in range(2):
            tasks = asyncio.gather(*[x.update_status() for x in self.test_system.assets.assets])
            self.loop.run_until_complete(tasks)

            self.test_system.run_processes()

            tasks = asyncio.gather(*[x.update_control() for x in self.test_system.assets.assets])
            self.loop.run_until_complete(tasks)

        search_param = ('ess', 0, 'status', 'soc')
        resp = self.test_system.assets.get_asset(search_param[0])

        self.assertGreater(getattr(resp[0], search_param[2])[search_param[3]], 0.0)

    def test_GraphDependencies_sort(self):
        logging.debug('********** Test process: test_graph_dependencies **********')
        self.test_system.process.sort()



class TestGraphProcess(unittest.TestCase):
    def setUp(self):
        self.test_system = gridpi_core.System()  # Create System container object

        # configure processes
        parser = ConfigParser()
        parser.read_dict({'process_1': {'class_name': 'EssUpdateStatus'},
                               'process_2': {'class_name': 'GridUpdateStatus'},
                               'process_3': {'class_name': 'EssSocPowerController',
                                             'inverter_target_soc': 0.6},
                               'process_4': {'class_name': 'EssDemandLimitPowerController',
                                             'grid_kw_import_limit': 20,
                                             'grid_kw_export_limit': 20},
                               'process_5': {'class_name': 'EssWriteControl'}})
        process_factory = process_core.ProcessFactory()
        for cfg in parser.sections():
            self.test_system.add_process(process_factory.factory(parser[cfg]))
        del process_factory

    def test_Edgenode_constructor(self):
        node1 = process_graph.Edgenode()
        node2 = process_graph.Edgenode()

        node1.name = 'first_node'
        node2.name = 'second_node'

        node1.next = node2

        self.assertEqual(node1.next, node2)
        self.assertEqual(node1.next.name, 'second_node')

    def test_Graph_constructor(self):
        pass

    def test_Graph_buildAdjList(self):
        pass

    def test_Graph_insertEdge(self):
        pass

    def test_Graph_topologicalSort(self):
        pass

    def test_GraphProcess_constructor(self):
        pass

    def test_DFS_constructor(self):
        pass

    def test_GraphDependencies_findInputSinks(self):
        pass

    def test_GraphDependencies_findOutputSources(self):
        pass

    def test_GraphDependencies_resolveDuplicateSources(self):
        pass

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    unittest.main()
