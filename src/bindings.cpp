#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include "solver.h"

namespace nb = nanobind;

NB_MODULE(vrp_core, m) {
    m.doc() = "VRP Solver C++ core module with Python bindings";
    
    nb::class_<Location>(m, "Location")
        .def(nb::init<double, double>())
        .def_rw("latitude", &Location::latitude)
        .def_rw("longitude", &Location::longitude);
    
    nb::class_<Customer>(m, "Customer")
        .def(nb::init<int, Location, double, double, double>(),
             nb::arg("id"),
             nb::arg("location"),
             nb::arg("demand"),
             nb::arg("start_window"),
             nb::arg("end_window"))
        .def(nb::init<int, Location, double, double, double, double>(),
             nb::arg("id"),
             nb::arg("location"),
             nb::arg("demand"),
             nb::arg("start_window"),
             nb::arg("end_window"),
             nb::arg("service_time"))
        .def_rw("id", &Customer::id)
        .def_rw("location", &Customer::location)
        .def_rw("demand", &Customer::demand)
        .def_rw("start_window", &Customer::start_window)
        .def_rw("end_window", &Customer::end_window)
        .def_rw("service_time", &Customer::service_time);
    
    nb::class_<VRPSolver>(m, "VRPSolver")
        .def(nb::init<>())
        .def("solve", &VRPSolver::solve,
             nb::arg("customers"),
             nb::arg("vehicle_capacities"),
             nb::arg("use_simd") = true,
             nb::arg("time_matrix") = std::vector<std::vector<double>>(),
             "Solve VRP with heterogeneous fleet, optional SIMD optimization and time matrix");
}
